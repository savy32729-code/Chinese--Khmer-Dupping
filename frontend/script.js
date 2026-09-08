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
        videoInfo.textContent = "មិនទាន់បានជ្រើស Video";
        duration.textContent = "";
        startBtn.disabled = true;
        return;
    }

    videoInfo.textContent =
        `📹 ${selectedFile.name}`;

    const sizeMB =
        (selectedFile.size / 1024 / 1024).toFixed(2);

    duration.textContent =
        `ទំហំ: ${sizeMB} MB`;

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
        alert("សូមជ្រើស Video ជាមុនសិន");
        return;
    }

    startBtn.disabled = true;

    progressCard.classList.remove("hidden");
    resultsCard.classList.add("hidden");

    setProgress(
        5,
        "កំពុង Upload Video..."
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
            throw new Error(
                "Upload Video បរាជ័យ"
            );
        }

        const uploadData =
            await uploadResponse.json();

        setProgress(
            20,
            "Upload បានជោគជ័យ..."
        );


        // =========================
        // 2. TRANSCRIBE
        // =========================

        const filename =
            uploadData.filename ||
            selectedFile.name;

        setProgress(
            30,
            "កំពុងស្តាប់សំឡេងក្នុង Video..."
        );

        const transcribeResponse =
            await fetch(
                `${API_URL}/transcribe?filename=${encodeURIComponent(filename)}`,
                {
                    method: "POST"
                }
            );

        if (!transcribeResponse.ok) {
            throw new Error(
                "Transcribe បរាជ័យ"
            );
        }

        const transcribeData =
            await transcribeResponse.json();

        let segments =
            transcribeData.segments || [];

        if (!segments.length) {
            throw new Error(
                "រកមិនឃើញសំឡេងក្នុង Video"
            );
        }


        // =========================
        // 3. TRANSLATE
        // =========================

        if (translateToggle.checked) {

            setProgress(
                45,
                "កំពុងបកប្រែ Chinese → Khmer..."
            );

            for (
                let i = 0;
                i < segments.length;
                i++
            ) {

                const segment =
                    segments[i];

                const translateResponse =
                    await fetch(
                        `${API_URL}/translate`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                text:
                                    segment.text || ""
                            })
                        }
                    );

                if (!translateResponse.ok) {
                    throw new Error(
                        "Translation បរាជ័យ"
                    );
                }

                const translateData =
                    await translateResponse.json();

                segment.translation =
                    translateData.translation ||
                    segment.text ||
                    "";

                const progress =
                    45 +
                    Math.round(
                        ((i + 1) /
                            segments.length) *
                        25
                    );

                setProgress(
                    progress,
                    `កំពុងបកប្រែ ${i + 1}/${segments.length}...`
                );
            }

        } else {

            segments.forEach(
                segment => {

                    segment.translation =
                        segment.text || "";

                }
            );

        }


        // =========================
        // 4. CREATE DUBBING
        // =========================

        setProgress(
            75,
            "កំពុងបង្កើតសំឡេងខ្មែរ..."
        );

        processingStatus.textContent =
            `🎙️ សំឡេង: ${voiceSelect.value}`;


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
                `Dubbing បរាជ័យ: ${errorText}`
            );

        }


        const dubbingData =
            await dubbingResponse.json();


        setProgress(
            95,
            "កំពុងរៀបចំ Video ចុងក្រោយ..."
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
            "រួចរាល់! 🎉"
        );


        saveBtn.href =
            videoUrl;

        partsList.innerHTML = "";


        const resultInfo =
            document.createElement("div");

        resultInfo.className =
            "result-item";

        resultInfo.textContent =
            "✅ Video Khmer ត្រូវបានបង្កើតរួចរាល់";

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
            "មានបញ្ហា សូមព្យាយាមម្តងទៀត"
        );

        progressText.textContent =
            "❌ មានបញ្ហា";

        processingStatus.textContent =
            error.message || "";

    } finally {

        startBtn.disabled = false;

    }

});
