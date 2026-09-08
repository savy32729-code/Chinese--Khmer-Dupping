const API_URL = "https://chinese-khmer-dupping.onrender.com";

const videoInput = document.getElementById("videoInput");

const videoInfo = document.getElementById("videoInfo");

const duration = document.getElementById("duration");

const translateToggle = document.getElementById("translateToggle");

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

let translatedSegments = [];

/* =====================================================

   Video Selected

===================================================== */

videoInput.addEventListener("change", function () {

    const file = this.files[0];

    if (!file) {

        selectedFile = null;

        return;

    }

    selectedFile = file;

    videoInfo.textContent =

        `Selected: ${file.name}`;

    if (duration) {

        duration.textContent =

            formatFileSize(file.size);

    }

    startBtn.disabled = false;

});

/* =====================================================

   Start Dubbing

===================================================== */

startBtn.addEventListener("click", async function () {

    if (!selectedFile) {

        alert("សូមជ្រើសរើសវីដេអូមុនសិន។");

        return;

    }

    try {

        startBtn.disabled = true;

        progressCard.style.display = "block";

        resultsCard.style.display = "none";

        updateProgress(

            5,

            "Uploading video..."

        );

        /* =============================================

           STEP 1 — Upload

        ============================================= */

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

                await getError(uploadResponse)

            );

        }

        const uploadResult =

            await uploadResponse.json();

        const filename =

            uploadResult.filename;

        /* =============================================

           STEP 2 — Transcribe

        ============================================= */

        updateProgress(

            30,

            "កំពុងស្តាប់សំឡេងចិន..."

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

                await getError(transcribeResponse)

            );

        }

        const transcription =

            await transcribeResponse.json();

        const segments =

            transcription.segments || [];

        /* =============================================

           STEP 3 — Translate

        ============================================= */

        updateProgress(

            55,

            "កំពុងបកប្រែចិន → ខ្មែរ..."

        );

        translatedSegments = [];

        for (

            let i = 0;

            i < segments.length;

            i++

        ) {

            const segment = segments[i];

            let khmerText =

                segment.text;

            if (

                translateToggle &&

                translateToggle.checked

            ) {

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

                                text: segment.text,

                                source: "zh",

                                target: "km"

                            })

                        }

                    );

                if (!translateResponse.ok) {

                    throw new Error(

                        await getError(

                            translateResponse

                        )

                    );

                }

                const result =

                    await translateResponse.json();

                khmerText =

                    result.translation ||

                    segment.text;

            }

            translatedSegments.push({

                start: segment.start,

                end: segment.end,

                original: segment.text,

                translation: khmerText

            });

            const percent =

                55 +

                Math.round(

                    ((i + 1) /

                        segments.length) *

                    25

                );

            updateProgress(

                percent,

                `កំពុងបកប្រែ ${i + 1}/${segments.length}...`

            );

        }

        /* =============================================

           STEP 4 — Khmer TTS

        ============================================= */

        updateProgress(

            85,

            "កំពុងបង្កើតសំឡេងខ្មែរ..."

        );

        for (

            let i = 0;

            i < translatedSegments.length;

            i++

        ) {

            const item =

                translatedSegments[i];

            if (!item.translation) {

                continue;

            }

            const ttsResponse =

                await fetch(

                    `${API_URL}/tts`,

                    {

                        method: "POST",

                        headers: {

                            "Content-Type":

                                "application/json"

                        },

                        body: JSON.stringify({

                            text: item.translation,

                            lang: "km"

                        })

                    }

                );

            if (!ttsResponse.ok) {

                throw new Error(

                    await getError(

                        ttsResponse

                    )

                );

            }

            const ttsResult =

                await ttsResponse.json();

            item.audioUrl =

                `${API_URL}${ttsResult.audio_url}`;

        }

        /* =============================================

           STEP 5 — Show Results

        ============================================= */

        updateProgress(

            100,

            "រួចរាល់! 🎉"

        );

        showResults();

    } catch (error) {

        console.error(

            "Dubbing Error:",

            error

        );

        alert(

            "មានបញ្ហា៖ " +

            error.message

        );

        updateProgress(

            0,

            "មានបញ្ហាក្នុងការដំណើរការ"

        );

    } finally {

        startBtn.disabled = false;

    }

});

/* =====================================================

   Progress

===================================================== */

function updateProgress(

    percent,

    text

) {

    if (progressFill) {

        progressFill.style.width =

            `${percent}%`;

    }

    if (percentage) {

        percentage.textContent =

            `${percent}%`;

    }

    if (progressText) {

        progressText.textContent =

            text;

    }

    if (processingStatus) {

        processingStatus.textContent =

            text;

    }

}

/* =====================================================

   Show Results

===================================================== */

function showResults() {

    if (!resultsCard) {

        return;

    }

    resultsCard.style.display =

        "block";

    partsList.innerHTML = "";

    if (

        translatedSegments.length === 0

    ) {

        partsList.innerHTML =

            `<p>រកមិនឃើញសំឡេងក្នុងវីដេអូទេ។</p>`;

        return;

    }

    translatedSegments.forEach(

        (item, index) => {

            const part =

                document.createElement("div");

            part.className =

                "result-part";

            part.innerHTML = `

                <div class="part-number">

                    ${index + 1}

                </div>

                <div class="part-content">

                    <div class="original-text">

                        ${escapeHtml(

                            item.original

                        )}

                    </div>

                    <div class="translation-text">

                        ${escapeHtml(

                            item.translation

                        )}

                    </div>

                    ${

                        item.audioUrl

                        ? `

                        <audio

                            controls

                            preload="none"

                            src="${item.audioUrl}">

                        </audio>

                        `

                        : ""

                    }

                </div>

            `;

            partsList.appendChild(

                part

            );

        }

    );

}

/* =====================================================

   Save Results

===================================================== */

if (saveBtn) {

    saveBtn.addEventListener(

        "click",

        function () {

            if (

                translatedSegments.length === 0

            ) {

                alert(

                    "មិនមានលទ្ធផលសម្រាប់រក្សាទុកទេ។"

                );

                return;

            }

            const text =

                translatedSegments

                    .map(

                        (item, index) =>

                            `${index + 1}. ${item.translation}`

                    )

                    .join("\n");

            const blob =

                new Blob(

                    [text],

                    {

                        type:

                            "text/plain;charset=utf-8"

                    }

                );

            const url =

                URL.createObjectURL(blob);

            const link =

                document.createElement("a");

            link.href = url;

            link.download =

                "chinese-khmer-dubbing.txt";

            document.body.appendChild(

                link

            );

            link.click();

            link.remove();

            URL.revokeObjectURL(url);

        }

    );

}

/* =====================================================

   Error Helper

===================================================== */

async function getError(

    response

) {

    try {

        const data =

            await response.json();

        return (

            data.detail ||

            data.message ||

            `Server error ${response.status}`

        );

    } catch {

        return (

            `Server error ${response.status}`

        );

    }

}

/* =====================================================

   File Size

===================================================== */

function formatFileSize(

    bytes

) {

    if (bytes === 0) {

        return "0 Bytes";

    }

    const units = [

        "Bytes",

        "KB",

        "MB",

        "GB"

    ];

    const i =

        Math.floor(

            Math.log(bytes) /

            Math.log(1024)

        );

    return (

        parseFloat(

            (

                bytes /

                Math.pow(1024, i)

            ).toFixed(2)

        ) +

        " " +

        units[i]

    );

}

/* =====================================================

   Escape HTML

===================================================== */

function escapeHtml(

    text

) {

    const div =

        document.createElement("div");

    div.textContent =

        text || "";

    return div.innerHTML;

}
