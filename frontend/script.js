const API_URL = "https://chinese-khmer-dupping.onrender.com";

const videoInput = document.getElementById("videoInput");
const videoInfo = document.getElementById("videoInfo");
const duration = document.getElementById("duration");
const translateToggle = document.getElementById("translateToggle");
const voiceSelect = document.getElementById("voiceSelect");
const startBtn = document.getElementById("startBtn");

const progressCard = document.getElementById("progressCard");
const progressFill = document.getElementById("progressFill");
const percentage = document.getElementById("percentage");
const progressText = document.getElementById("progressText");
const processingStatus = document.getElementById("processingStatus");

const resultsCard = document.getElementById("resultsCard");
const partsList = document.getElementById("partsList");
const saveBtn = document.getElementById("saveBtn");

let selectedFile = null;


// ================================
// VIDEO SELECT
// ================================

videoInput.addEventListener("change", () => {

    selectedFile = videoInput.files[0];

    if (!selectedFile) {
        videoInfo.textContent = "áá·ááá¶áááá¶ááááá¾á Video";
        duration.textContent = "";
        startBtn.disabled = true;
        return;
    }

    videoInfo.textContent =
        `ð¹ ${selectedFile.name}`;

    const sizeMB =
        (selectedFile.size / 1024 / 1024).toFixed(2);

    duration.textContent =
        `ááá á: ${sizeMB} MB`;

    startBtn.disabled = false;

});


// ================================
// PROGRESS
// ================================

function setProgress(value, text) {

    progressFill.style.width = `${value}%`;

    percentage.textContent =
        `${value}%`;

    progressText.textContent =
        text;

}


// ================================
// START DUBBING
// ================================

startBtn.addEventListener("click", async () => {

    if (!selectedFile) {
        alert("áá¼ááááá¾á Video áá¶áá»ááá·á");
        return;
    }

    startBtn.disabled = true;

    progressCard.classList.remove("hidden");
    resultsCard.classList.add("hidden");

    setProgress(
        5,
        "áááá»á Upload Video..."
    );

    try {

        // =========================
        // 1. UPLOAD
        // =========================

        const formData = new FormData();

        formData.append(
            "file",
            selectedFile
        );

        const uploadResponse =
            await fetch(
                `${API_URL}/upload`,
                {
                    method: "POST",
                    body: formData
                }
            );

        if (!uploadResponse.ok) {
            const errorText = await uploadResponse.text();
            throw new Error(`Upload Video ááá¶ááá: ${errorText}`);
        }

        const uploadData =
            await uploadResponse.json();

        setProgress(
            20,
            "Upload áá¶ááááááá..."
        );


        // =========================
        // 2. TRANSCRIBE
        // =========================

        const filename =
            uploadData.filename ||
            selectedFile.name;

        setProgress(
            30,
            "áááá»ááááá¶ááááá¡áááááá»á Video..."
        );

        const transcribeResponse =
            await fetch(
                `${API_URL}/transcribe?filename=${encodeURIComponent(filename)}`,
                {
                    method: "POST"
                }
            );

        if (!transcribeResponse.ok) {
            const errorText = await transcribeResponse.text();
            throw new Error(`Transcribe ááá¶ááá: ${errorText}`);
        }

        const transcribeData =
            await transcribeResponse.json();

        let segments =
            transcribeData.segments || [];

        if (!segments.length) {
            throw new Error(
                "áááá·ááá¾áááá¡áááááá»á Video"
            );
        }


        // =========================
        // 3. TRANSLATE
        // =========================

        if (translateToggle.checked) {

            setProgress(
                45,
                `áááá»ááááááá ${segments.length} áááááá...`
            );

            const translateResponse = await fetch(
                `${API_URL}/translate`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        source: "zh",
                        target: "km",
                        segments: segments.map(s => ({
                            start: Number(s.start) || 0,
                            end: Number(s.end) || 0,
                            text: s.text || ""
                        }))
                    })
                }
            );

            if (!translateResponse.ok) {
                const errorText = await translateResponse.text();
                throw new Error(
                    `Translation ááá¶ááá: ${errorText}`
                );
            }

            const translateData = await translateResponse.json();
            const translated = translateData.segments || [];

            if (!translated.length) {
                throw new Error("áá·áá¢á¶ááááááááá¶á");
            }

            segments = translated;
            setProgress(
                70,
                `áááááááá½ááá¶áá ${translated.length} áááááá`
            );

        } else {

            segments.forEach(segment => {
                segment.translation = segment.text || "";
            });

        }


        // =========================
        // 4. CREATE DUBBING
        // =========================

        setProgress(
            75,
            "áááá»áááááá¾áááá¡ááááááá..."
        );

        processingStatus.textContent =
            `ðï¸ ááá¡áá: ${voiceSelect.value}`;


        const dubbingResponse =
            await fetch(
                `${API_URL}/create-dubbing`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        filename: filename,

                        voice:
                            voiceSelect.value,

                        segments:
                            segments

                    })
                }
            );


        if (!dubbingResponse.ok) {

            const errorText =
                await dubbingResponse.text();

            throw new Error(
                `Dubbing ááá¶ááá: ${errorText}`
            );

        }


        const dubbingData =
            await dubbingResponse.json();


        setProgress(
            95,
            "áááá»áááááá Video áá»áááááá..."
        );


        // =========================
        // 5. RESULT
        // =========================

        const outputFilename =
            dubbingData.filename ||
            filename;

        const videoUrl =
            `${API_URL}/video/${encodeURIComponent(outputFilename)}`;


        setProgress(
            100,
            "áá½ááá¶áá! ð"
        );


        saveBtn.href =
            videoUrl;

        partsList.innerHTML = "";


        const resultInfo =
            document.createElement("div");

        resultInfo.className =
            "result-item";

        resultInfo.textContent =
            "â Video Khmer áááá¼ááá¶áááááá¾ááá½ááá¶áá";

        partsList.appendChild(
            resultInfo
        );


        resultsCard.classList.remove(
            "hidden"
        );


    } catch (error) {

        console.error(error);

        alert(
            error.message ||
            "áá¶ááááá á¶ áá¼ááááá¶áá¶áááááááá"
        );

        progressText.textContent =
            "â áá¶ááááá á¶";

        processingStatus.textContent =
            error.message || "";

    } finally {

        startBtn.disabled = false;

    }

});
