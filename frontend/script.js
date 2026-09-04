const videoInput = document.getElementById("videoInput");

const videoInfo = document.getElementById("videoInfo");

const durationInput = document.getElementById("duration");

const voiceButtons = document.querySelectorAll(".voice-btn");

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


let selectedVoice = "Auto";

let selectedVideo = null;

let videoDuration = 0;


/* =========================================
   VIDEO UPLOAD
========================================= */

videoInput.addEventListener("change", function () {

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

        const minutes =
            Math.floor(videoDuration / 60);

        const seconds =
            Math.floor(videoDuration % 60);

        videoInfo.classList.remove("hidden");

        videoInfo.innerHTML = 
            <strong>🎬 ${file.name}</strong>
            <br>
            📦 Size:
            ${formatFileSize(file.size)}
            <br>
            ⏱️ Duration:
            ${minutes}m ${seconds}s
        ;
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

        selectedVoice =
            this.dataset.voice;

    });

});


/* =========================================
   START
========================================= */

startBtn.addEventListener("click", function () {

    if (!selectedVideo) {

        alert(
            "Please choose a video first."
        );

        return;
    }


    let duration =
        parseInt(durationInput.value);


    if (!duration || duration < 1) {

        alert(
            "Please enter a valid duration."
        );

        return;
    }


    /* Limit to 3 minutes for now */

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


    progressText.textContent =
        "Preparing video...";

    processingStatus.textContent =
        "Preparing video...";


    simulateRendering(duration);

});


/* =========================================
   RENDERING SIMULATION
========================================= */

function simulateRendering(duration) {

    let progress = 0;


    const steps = [

        {
            percent: 10,
            text: "Uploading video..."
        },

        {
            percent: 25,
            text: "Reading video..."
        },
   {
            percent: 40,
            text: "Detecting languages..."
        },

        {
            percent: 55,
            text: "Translating to Khmer..."
        },

        {
            percent: 70,
            text:
                "Generating " +
                selectedVoice +
                " voice..."
        },

        {
            percent: 82,
            text: "Creating 3-minute parts..."
        },

        {
            percent: 94,
            text: "Rendering video..."
        },

        {
            percent: 100,
            text: "Completed!"
        }

    ];


    let index = 0;


    const timer = setInterval(() => {

        if (index >= steps.length) {

            clearInterval(timer);

            finishRendering(duration);

            return;
        }


        const step = steps[index];

        progress = step.percent;


        progressFill.style.width =
            progress + "%";

        percentage.textContent =
            progress + "%";

        progressText.textContent =
            step.text;

        processingStatus.textContent =
            step.text;


        index++;

    }, 900);

}


/* =========================================
   FINISH
========================================= */

function finishRendering(duration) {

    startBtn.disabled = false;

    createParts(duration);

    resultsCard.classList.remove(
        "hidden"
    );

    progressText.textContent =
        "Rendering completed.";

    processingStatus.textContent =
        "All videos are ready.";

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


        const part = document.createElement(
            "div"
        );

        part.className = "part";


        part.innerHTML = 

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

        ;


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
        ":" +
        String(secs).padStart(2, "0")
    );

}


/* =========================================
   SAVE
========================================= */

saveBtn.addEventListener(
    "click",
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

            shortDuration:
                durationInput.value +
                " minutes",
        status:
                "Rendering completed"

        };


        const blob = new Blob(

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
);  
