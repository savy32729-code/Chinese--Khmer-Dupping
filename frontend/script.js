const API_URL = “https://chinese-khmer-dupping.onrender.com”;

const videoInput = document.getElementById(“videoInput”);
const videoInfo = document.getElementById(“videoInfo”);
const durationInput = document.getElementById(“duration”);
const voiceButtons = document.querySelectorAll(”.voice-btn”);
const translateToggle = document.getElementById(“translateToggle”);
const startBtn = document.getElementById(“startBtn”);
const progressCard = document.getElementById(“progressCard”);
const progressFill = document.getElementById(“progressFill”);
const percentage = document.getElementById(“percentage”);
const progressText = document.getElementById(“progressText”);
const processingStatus = document.getElementById(“processingStatus”);
const resultsCard = document.getElementById(“resultsCard”);
const partsList = document.getElementById(“partsList”);
const saveBtn = document.getElementById(“saveBtn”);

let selectedVoice = “Auto”;
let selectedVideo = null;
let videoDuration = 0;
let uploadedFilename = null;
let transcriptionResult = null;
let translationResult = null;
let audioUrl = null;

/* =========================================
VIDEO UPLOAD / VIDEO INFORMATION
========================================= */

videoInput.addEventListener(“change”, function () {
const file = this.files[0];

if (!file) {
    return;
}

selectedVideo = file;

const video = document.createElement("video");

video.preload = "metadata";

video.onloadedmetadata = function () {

    window.URL.revokeObjectURL(video.src);

    videoDuration = video.duration;

    const minutes = Math.floor(videoDuration / 60);
    const seconds = Math.floor(videoDuration % 60);

    videoInfo.classList.remove("hidden");

    videoInfo.innerHTML = `
        <strong>🎬 ${file.name}</strong>
        <br>
        📦 Size: ${formatFileSize(file.size)}
        <br>
        ⏱️ Duration: ${minutes}m ${seconds}s
    `;
};

video.src = URL.createObjectURL(file);
});

/* =========================================
FILE SIZE
========================================= */

function formatFileSize(bytes) {
if (bytes < 1024 * 1024) {

    return (
        bytes / 1024
    ).toFixed(1) + " KB";

}

return (
    bytes / (1024 * 1024)
).toFixed(2) + " MB";
}

/* =========================================
VOICE SELECT
========================================= */

voiceButtons.forEach(button => {
button.addEventListener("click", function () {

    voiceButtons.forEach(btn => {
        btn.classList.remove("active");
    });

    this.classList.add("active");

    selectedVoice = this.dataset.voice;

});
});

/* =========================================
START REAL PROCESSING
========================================= */

startBtn.addEventListener(“click”, async function () {
if (!selectedVideo) {

    alert("Please choose a video first.");

    return;
}


let duration = parseInt(durationInput.value);


if (!duration || duration < 1) {

    alert("Please enter a valid duration.");

    return;
}


if (duration > 3) {

    duration = 3;

    durationInput.value = 3;

    alert(
        "Short video duration is limited to 3 minutes."
    );
}


startBtn.disabled = true;

progressCard.classList.remove("hidden");

resultsCard.classList.add("hidden");

progressFill.style.width = "0%";

percentage.textContent = "0%";

progressText.textContent = "Connecting to backend...";

processingStatus.textContent = "Connecting to backend...";


try {

    /* ================================
       STEP 1: UPLOAD VIDEO
    ================================= */

    updateProgress(
        10,
        "Uploading video..."
    );


    const formData = new FormData();

    formData.append(
        "file",
        selectedVideo
    );


    const uploadResponse = await fetch(
        `${API_URL}/upload`,
        {
            method: "POST",
            body: formData
        }
    );


    if (!uploadResponse.ok) {

        throw new Error(
            "Video upload failed."
        );
    }


    const uploadData =
        await uploadResponse.json();


    uploadedFilename =
        uploadData.filename;


    /* ================================
       STEP 2: TRANSCRIBE CHINESE
    ================================= */

    updateProgress(
        30,
        "Converting Chinese speech to text..."
    );


    const transcribeResponse =
        await fetch(
            `${API_URL}/transcribe?filename=${encodeURIComponent(uploadedFilename)}`,
            {
                method: "POST"
            }
        );


    if (!transcribeResponse.ok) {

        throw new Error(
            "Chinese transcription failed."
        );
    }


    transcriptionResult =
        await transcribeResponse.json();


    /* ================================
       STEP 3: TRANSLATE TO KHMER
    ================================= */

    if (translateToggle.checked) {

        updateProgress(
            55,
            "Translating Chinese to Khmer..."
        );


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
                            transcriptionResult.text,

                        source: "zh",

                        target: "km"

                    })
                }
            );


        if (!translateResponse.ok) {

            throw new Error(
                "Khmer translation failed."
            );
        }


        translationResult =
            await translateResponse.json();


        /* ================================
           STEP 4: KHMER TEXT TO SPEECH
        ================================= */

        updateProgress(
            75,
            "Generating Khmer voice..."
        );

console.log("TTS BODY:".{text:translationResult. translation,
    lang: "km"
   }),
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

                        text:
                            translationResult.translation,

                        lang: "km"

                    })
                }
            );


        if (!ttsResponse.ok) {
        const errorData = await
        ttsResponse. json();
            console. log("TTS ERROR:",errorData);
            throw new Error(JSON.stringify(errorData));}

        const ttsData =
            await ttsResponse.json();


        audioUrl =
            `${API_URL}${ttsData.audio_url}`;

    }


    /* ================================
       STEP 5: SHOW RESULT
    ================================= */

    updateProgress(
        90,
        "Preparing results..."
    );


    createParts(duration);


    showTranscript();


    updateProgress(
        100,
        "Completed!"
    );


    resultsCard.classList.remove(
        "hidden"
    );


    processingStatus.textContent =
        "Chinese video processed successfully.";


} catch (error) {

    console.error(error);

    alert(
        "Processing failed: " +
        error.message
    );

    progressText.textContent =
        "Processing failed.";

    processingStatus.textContent =
        error.message;

} finally {

    startBtn.disabled = false;

}
});

/* =========================================
PROGRESS
========================================= */

function updateProgress(
value,
text
) {
progressFill.style.width =
    value + "%";

percentage.textContent =
    value + "%";

progressText.textContent =
    text;

processingStatus.textContent =
    text;
}

/* =========================================
SHOW TRANSCRIPT
========================================= */

function showTranscript() {
if (!transcriptionResult) {
    return;
}


const transcript =
    document.createElement("div");

transcript.className =
    "transcript-result";


const originalTitle =
    document.createElement("h3");

originalTitle.textContent =
    "🇨🇳 Chinese Transcript";


const originalText =
    document.createElement("p");

originalText.textContent =
    transcriptionResult.text;


transcript.appendChild(
    originalTitle
);

transcript.appendChild(
    originalText
);


if (
    translationResult &&
    translationResult.translation
) {

    const translatedTitle =
        document.createElement("h3");

    translatedTitle.textContent =
        "🇰🇭 Khmer Translation";


    const translatedText =
        document.createElement("p");

    translatedText.textContent =
        translationResult.translation;


    transcript.appendChild(
        translatedTitle
    );

    transcript.appendChild(
        translatedText
    );

}


if (audioUrl) {

    const audioTitle =
        document.createElement("h3");

    audioTitle.textContent =
        "🔊 Khmer Voice";


    const audio =
        document.createElement("audio");

    audio.controls = true;

    audio.src = audioUrl;


    transcript.appendChild(
        audioTitle
    );

    transcript.appendChild(
        audio
    );

}


resultsCard.prepend(
    transcript
);
}

/* =========================================
CREATE VIDEO PART LIST
========================================= */

function createParts(durationMinutes) {
partsList.innerHTML = "";

let numberOfParts = 1;


if (videoDuration > 0) {

    numberOfParts =
        Math.ceil(
            videoDuration /
            (durationMinutes * 60)
        );

}


for (
    let i = 1;
    i <= numberOfParts;
    i++
) {

    const start =
        (i - 1) *
        durationMinutes *
        60;


    const end =
        Math.min(
            i *
            durationMinutes *
            60,
            videoDuration
        );


    const part =
        document.createElement("div");


    part.className =
        "part";


    part.innerHTML = `

        <div class="part-info">

            <div class="part-icon">
                🎬
            </div>

            <div>

                <strong>
                    Short Video ${i}
                </strong>

                <small>
                    ${formatTime(start)}
                    -
                    ${formatTime(end)}
                </small>

            </div>

        </div>

        <div class="part-status">
            ✓ Ready
        </div>

    `;


    partsList.appendChild(part);

}
}

/* =========================================
FORMAT TIME
========================================= */

function formatTime(seconds) {
const mins =
    Math.floor(seconds / 60);

const secs =
    Math.floor(seconds % 60);


return (
    String(mins).padStart(2, "0")
    +
    ":"
    +
    String(secs).padStart(2, "0")
);
}

/* =========================================
SAVE PROJECT
========================================= */

saveBtn.addEventListener(
“click”,
function () {
    const information = {

        website:
            "Chinese → Khmer Dubbing",

        originalVideo:
            selectedVideo
                ? selectedVideo.name
                : null,

        voice:
            selectedVoice,

        translateTo:
            translateToggle.checked
                ? "Khmer"
                : "Disabled",

        chineseTranscript:
            transcriptionResult
                ? transcriptionResult.text
                : null,

        khmerTranslation:
            translationResult
                ? translationResult.translation
                : null,

        audio:
            audioUrl,

        shortDuration:
            durationInput.value +
            " minutes",

        status:
            "Rendering completed"

    };


    const blob =
        new Blob(
            [
                JSON.stringify(
                    information,
                    null,
                    2
                )
            ],
            {
                type:
                    "application/json"
            }
        );


    const url =
        URL.createObjectURL(blob);


    const a =
        document.createElement("a");


    a.href = url;

    a.download =
        "dubbing-project.json";


    a.click();


    URL.revokeObjectURL(url);

}
