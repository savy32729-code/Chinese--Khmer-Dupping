const API_URL = "https://chinese-khmer-dupping.onrender.com";

const videoInput = document.getElementById("videoInput");

const videoInfo = document.getElementById("videoInfo");

const duration = document.getElementById("duration");

const translateToggle =

    document.getElementById("translateToggle");

const startBtn =

    document.getElementById("startBtn");

const progressCard =

    document.getElementById("progressCard");

const progressFill =

    document.getElementById("progressFill");

const percentage =

    document.getElementById("percentage");

const progressText =

    document.getElementById("progressText");

const processingStatus =

    document.getElementById("processingStatus");

const resultsCard =

    document.getElementById("resultsCard");

const partsList =

    document.getElementById("partsList");

const saveBtn =

    document.getElementById("saveBtn");

let selectedFile = null;

let translatedSegments = [];

let finalVideoUrl = null;

/* =====================================================

   Select Video

===================================================== */

videoInput.addEventListener(

    "change",

    function () {

        const file = this.files[0];

        if (!file) {

            selectedFile = null;

            startBtn.disabled = true;

            return;

        }

        selectedFile = file;

        videoInfo.textContent =

            `📹 ${file.name}`;

        duration.textContent =

            formatFileSize(file.size);

        startBtn.disabled = false;

        resultsCard.style.display =

            "none";

    }

);

/* =====================================================

   Start Dubbing

===================================================== */

startBtn.addEventListener(

    "click",

    async function () {

        if (!selectedFile) {

            alert(

                "សូមជ្រើសរើសវីដេអូមុនសិន។"

            );

            return;

        }

        try {

            startBtn.disabled = true;

            progressCard.style.display =

                "block";

            resultsCard.style.display =

                "none";

            finalVideoUrl = null;

            /* -----------------------------------------

               STEP 1 — Upload

            ----------------------------------------- */

            updateProgress(

                5,

                "កំពុង Upload វីដេអូ..."

            );

            const formData =

                new FormData();

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

                    await getError(

                        uploadResponse

                    )

                );

            }

            const uploadResult =

                await uploadResponse.json();

            const filename =

                uploadResult.filename;

            /* -----------------------------------------

               STEP 2 — Transcription

            ----------------------------------------- */

            updateProgress(

                25,

                "🎧 កំពុងស្តាប់សំឡេងចិន..."

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

                    await getError(

                        transcribeResponse

                    )

                );

            }

            const transcription =

                await transcribeResponse.json();

            const segments =

                transcription.segments || [];

            if (segments.length === 0) {

                throw new Error(

                    "មិនអាចរកឃើញសំឡេងចិនក្នុងវីដេអូទេ។"

                );

            }

            /* -----------------------------------------

               STEP 3 — Translate

            ----------------------------------------- */

            translatedSegments = [];

            for (

                let i = 0;

                i < segments.length;

                i++

            ) {

                const segment =

                    segments[i];

                let khmerText =

                    segment.text;

                if (

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

                                body:

                                    JSON.stringify({

                                        text:

                                            segment.text,

                                        source:

                                            "zh",

                                        target:

                                            "km"

                                    })

                            }

                        );

                    if (

                        !translateResponse.ok

                    ) {

                        throw new Error(

                            await getError(

                                translateResponse

                            )

                        );

                    }

                    const translateResult =

                        await translateResponse.json();

                    khmerText =

                        translateResult.translation ||

                        segment.text;

                }

                translatedSegments.push({

                    start:

                        Number(segment.start),

                    end:

                        Number(segment.end),

                    original:

                        segment.text,

                    translation:

                        khmerText

                });

                const percent =

                    30 +

                    Math.round(

                        (

                            (i + 1) /

                            segments.length

                        ) * 30

                    );

                updateProgress(

                    percent,

                    `🌐 បកប្រែ ${i + 1}/${segments.length}...`

                );

            }

            /* -----------------------------------------

               STEP 4 — Create Final Dubbing Video

            ----------------------------------------- */

            updateProgress(

                65,

                "🎙️ កំពុងបង្កើតសំឡេងខ្មែរ..."

            );

            const dubbingResponse =

                await fetch(

                    `${API_URL}/create-dubbing`,

                    {

                        method: "POST",

                        headers: {

                            "Content-Type":

                                "application/json"

                        },

                        body:

                            JSON.stringify({

                                filename:

                                    filename,

                                segments:

                                    translatedSegments

                            })

                    }

                );

            if (!dubbingResponse.ok) {

                throw new Error(

                    await getError(

                        dubbingResponse

                    )

                );

            }

            const dubbingResult =

                await dubbingResponse.json();

            if (

                !dubbingResult.success ||

                !dubbingResult.video_url

            ) {

                throw new Error(

                    "Server មិនបានបង្កើត Final Video ទេ។"

                );

            }

            finalVideoUrl =

                `${API_URL}${dubbingResult.video_url}`;

            /* -----------------------------------------

               STEP 5 — Complete

            ----------------------------------------- */

            updateProgress(

                100,

                "🎉 Final Video រួចរាល់!"

            );

            showFinalVideo(

                finalVideoUrl

            );

        } catch (error) {

            console.error(

                "Dubbing Error:",

                error

            );

            updateProgress(

                0,

                "❌ មានបញ្ហា"

            );

            alert(

                "មានបញ្ហា៖\n\n" +

                error.message

            );

        } finally {

            startBtn.disabled = false;

        }

    }

);

/* =====================================================

   Show Final Video

===================================================== */

function showFinalVideo(

    videoUrl

) {

    resultsCard.style.display =

        "block";

    partsList.innerHTML = "";

    const title =

        document.createElement(

            "h3"

        );

    title.textContent =

        "🎬 Final Khmer Dubbed Video";

    title.style.marginBottom =

        "12px";

    const video =

        document.createElement(

            "video"

        );

    video.controls = true;

    video.playsInline = true;

    video.preload = "metadata";

    video.src =

        videoUrl;

    video.style.width =

        "100%";

    video.style.borderRadius =

        "14px";

    video.style.background =

        "#000";

    const download =

        document.createElement(

            "a"

        );

    download.href =

        videoUrl;

    download.download =

        "khmer-dubbed-video.mp4";

    download.target =

        "_blank";

    download.className =

        "secondary-btn";

    download.style.display =

        "flex";

    download.style.alignItems =

        "center";

    download.style.justifyContent =

        "center";

    download.style.textDecoration =

        "none";

    download.textContent =

        "📥 បើក / រក្សាទុក Final MP4";

    partsList.appendChild(

        title

    );

    partsList.appendChild(

        video

    );

    partsList.appendChild(

        download

    );

}

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

   Error

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

            `Server Error ${response.status}`

        );

    } catch {

        return (

            `Server Error ${response.status}`

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
