/* =========================================================
   QUICKVAULT MAIN JAVASCRIPT
   File: static/js/main.js
   ========================================================= */


/* ===== 01. ELEMENT REFERENCES START ===== */

const fileInput =
    document.getElementById("fileInput");

const fileDropArea =
    document.getElementById("fileDropArea");

const selectedFile =
    document.getElementById("selectedFile");

const selectedFileName =
    document.getElementById(
        "selectedFileName"
    );

const selectedFileSize =
    document.getElementById(
        "selectedFileSize"
    );

const removeFileButton =
    document.getElementById(
        "removeFileButton"
    );

const uploadForm =
    document.getElementById(
        "uploadForm"
    );

const secureUploadButton =
    document.querySelector(
        ".secure-upload-button"
    );


/* ===== DOWNLOAD MODAL REFERENCES START ===== */

const openDownloadButton =
    document.getElementById(
        "openDownloadButton"
    );

const downloadModal =
    document.getElementById(
        "downloadModal"
    );

const closeDownloadButton =
    document.getElementById(
        "closeDownloadButton"
    );

const downloadForm =
    document.getElementById(
        "downloadForm"
    );


/* ===== SUCCESS MODAL REFERENCES START ===== */

const successModal =
    document.getElementById(
        "successModal"
    );

const closeSuccessButton =
    document.getElementById(
        "closeSuccessButton"
    );

const copyCodeButton =
    document.getElementById(
        "copyCodeButton"
    );

const copyStatusMessage =
    document.getElementById(
        "copyStatusMessage"
    );

const uploadAnotherButton =
    document.getElementById(
        "uploadAnotherButton"
    );

const downloadNowButton =
    document.getElementById(
        "downloadNowButton"
    );

const successAccessCode =
    document.getElementById(
        "successAccessCode"
    );

const successFileName =
    document.getElementById(
        "successFileName"
    );

const successFileSize =
    document.getElementById(
        "successFileSize"
    );

const successPinStatus =
    document.getElementById(
        "successPinStatus"
    );

const successExpiry =
    document.getElementById(
        "successExpiry"
    );

const successDownloadType =
    document.getElementById(
        "successDownloadType"
    );

const selectedFileIcon =
    document.querySelector(
        ".selected-file-icon"
    );

/* ===== 01. ELEMENT REFERENCES END ===== */

/* ===== QR AND COUNTDOWN REFERENCES START ===== */

const successQrCode =
    document.getElementById(
        "successQrCode"
    );

const expiryCountdown =
    document.getElementById(
        "expiryCountdown"
    );

/* ===== QR AND COUNTDOWN REFERENCES END ===== */

/* ===== UPLOAD PROGRESS REFERENCES START ===== */

const uploadProgressWrapper =
    document.getElementById(
        "uploadProgressWrapper"
    );

const uploadProgressBar =
    document.getElementById(
        "uploadProgressBar"
    );

const uploadProgressPercent =
    document.getElementById(
        "uploadProgressPercent"
    );

const uploadProgressText =
    document.getElementById(
        "uploadProgressText"
    );

const cancelUploadButton =
    document.getElementById(
        "cancelUploadButton"
    );

/* ===== UPLOAD PROGRESS REFERENCES END ===== */

/* ===== 02. GLOBAL DATA START ===== */

let latestAccessCode = "";

let expiryCountdownInterval = null;

let activeUploadRequest = null;

/* ===== 02. GLOBAL DATA END ===== */


/* ===== 03. FILE SIZE FORMATTER START ===== */

function formatFileSize(bytes) {

    if (bytes === 0) {

        return "0 Bytes";

    }

    const unit = 1024;

    const sizes = [
        "Bytes",
        "KB",
        "MB",
        "GB"
    ];

    const index = Math.floor(
        Math.log(bytes)
        /
        Math.log(unit)
    );

    return (
        parseFloat(
            (
                bytes
                /
                Math.pow(unit, index)
            ).toFixed(2)
        )
        +
        " "
        +
        sizes[index]
    );

}

/* ===== 03. FILE SIZE FORMATTER END ===== */

/* ===== 03A. FILE TYPE ICON START ===== */

function updateFileTypeIcon(filename) {

    const extension =
        filename
        .split(".")
        .pop()
        .toLowerCase();

    selectedFileIcon.className =
        "selected-file-icon";

    if (extension === "pdf") {

        selectedFileIcon.textContent = "📕";

        selectedFileIcon.classList.add(
            "file-pdf"
        );

    } else if (
        ["jpg","jpeg","png"].includes(
            extension
        )
    ) {

        selectedFileIcon.textContent = "🖼️";

        selectedFileIcon.classList.add(
            "file-image"
        );

    } else if (
        ["doc","docx","txt"].includes(
            extension
        )
    ) {

        selectedFileIcon.textContent = "📘";

        selectedFileIcon.classList.add(
            "file-document"
        );

    } else if (
        ["xls","xlsx"].includes(
            extension
        )
    ) {

        selectedFileIcon.textContent = "📊";

        selectedFileIcon.classList.add(
            "file-spreadsheet"
        );

    } else if (
        ["ppt","pptx"].includes(
            extension
        )
    ) {

        selectedFileIcon.textContent = "📙";

        selectedFileIcon.classList.add(
            "file-presentation"
        );

    } else if (extension === "zip") {

        selectedFileIcon.textContent = "🗜️";

        selectedFileIcon.classList.add(
            "file-archive"
        );

    } else {

        selectedFileIcon.textContent = "📄";

    }

}

/* ===== 03A. FILE TYPE ICON END ===== */

/* ===== 04. SELECTED FILE DISPLAY START ===== */

function showSelectedFile(file) {

    if (!file) {

        return;

    }

    const maximumSize =
        10 * 1024 * 1024;

    if (file.size > maximumSize) {

        showToast(
            "error",
            "File too large",
            "Maximum allowed file size is 10 MB."
        );

        fileInput.value = "";

        return;

    }
    const allowedExtensions = [
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "zip"
];

const fileExtension =
    file.name
    .split(".")
    .pop()
    .toLowerCase();

if (
    !allowedExtensions.includes(
        fileExtension
    )
) {

    showToast(
        "error",
        "Unsupported file type",
        "This file type is not allowed."
    );

    fileInput.value = "";

    return;

}

    selectedFileName.textContent =
        file.name;

    updateFileTypeIcon(
    file.name
    );

    selectedFileSize.textContent =
        formatFileSize(file.size);

    selectedFile.classList.add(
        "show"
    );

}

/* ===== 04. SELECTED FILE DISPLAY END ===== */


/* ===== 05. FILE INPUT EVENT START ===== */

fileInput.addEventListener(
    "change",
    function () {

        const file =
            fileInput.files[0];

        showSelectedFile(file);

    }
);

/* ===== 05. FILE INPUT EVENT END ===== */


/* ===== 06. REMOVE FILE EVENT START ===== */

removeFileButton.addEventListener(
    "click",
    function () {

        resetSelectedFileDisplay();

    }
);

/* ===== 06. REMOVE FILE EVENT END ===== */


/* ===== 07. RESET SELECTED FILE START ===== */

function resetSelectedFileDisplay() {

    fileInput.value = "";

    selectedFile.classList.remove(
        "show"
    );

    selectedFileName.textContent =
        "No file selected";

    selectedFileSize.textContent =
        "Select a file to continue";

    selectedFileIcon.className =
    "selected-file-icon";

    selectedFileIcon.textContent =
    "📄";

}

/* ===== 07. RESET SELECTED FILE END ===== */


/* ===== 08. DRAG AND DROP EVENTS START ===== */

fileDropArea.addEventListener(
    "dragover",
    function (event) {

        event.preventDefault();

        fileDropArea.classList.add(
            "drag-active"
        );

    }
);


fileDropArea.addEventListener(
    "dragleave",
    function () {

        fileDropArea.classList.remove(
            "drag-active"
        );

    }
);


fileDropArea.addEventListener(
    "drop",
    function (event) {

        event.preventDefault();

        fileDropArea.classList.remove(
            "drag-active"
        );

        const droppedFiles =
            event.dataTransfer.files;

        if (
            droppedFiles.length === 0
        ) {

            return;

        }

        const droppedFile =
            droppedFiles[0];

        const dataTransfer =
            new DataTransfer();

        dataTransfer.items.add(
            droppedFile
        );

        fileInput.files =
            dataTransfer.files;

        showSelectedFile(
            droppedFile
        );

    }
);

/* ===== 08. DRAG AND DROP EVENTS END ===== */


/* ========================================================= */
/* ===== 09. REAL FILE UPLOAD WITH PROGRESS START ===== */
/* ========================================================= */

uploadForm.addEventListener(
    "submit",
    function (event) {

        event.preventDefault();

        const file =
            fileInput.files[0];

        if (!file) {

            showToast(
                "error",
                "No file selected",
                "Please select a file before uploading."
            );

            return;

        }

        const maximumSize =
            10 * 1024 * 1024;

        if (file.size > maximumSize) {

            showToast(
                "error",
                "File too large",
                "Maximum allowed file size is 10 MB."
            );

            return;

        }

        const expiryTime =
            document.getElementById(
                "expiryTime"
            ).value;

        const filePin =
            document.getElementById(
                "filePin"
            ).value.trim();

        const oneTimeDownload =
            document.getElementById(
                "oneTimeDownload"
            ).checked;

        if (
            filePin !== ""
            &&
            !/^[0-9]{4}$/.test(
                filePin
            )
        ) {

            showToast(
                "error",
                "Invalid PIN",
                "PIN must contain exactly 4 digits."
            );

            return;

        }

        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "expiry_time",
            expiryTime
        );

        formData.append(
            "file_pin",
            filePin
        );

        formData.append(
            "one_time_download",
            oneTimeDownload
        );

        const request =
            new XMLHttpRequest();

        activeUploadRequest =
            request;

        const originalButtonContent =
            secureUploadButton.innerHTML;

        secureUploadButton.disabled =
            true;

        secureUploadButton.innerHTML =
            `
            <span class="upload-button-loader"></span>
            Uploading...
            `;

        uploadProgressWrapper.classList.add(
            "show"
        );

        uploadProgressBar.style.width =
            "0%";

        uploadProgressPercent.textContent =
            "0%";

        uploadProgressText.textContent =
            "Preparing upload...";


        /* ===== UPLOAD PROGRESS EVENT START ===== */

        request.upload.addEventListener(
            "progress",
            function (progressEvent) {

                if (
                    !progressEvent.lengthComputable
                ) {

                    return;

                }

                const uploadPercent =
                    Math.round(
                        (
                            progressEvent.loaded
                            /
                            progressEvent.total
                        )
                        *
                        100
                    );

                uploadProgressBar.style.width =
                    uploadPercent + "%";

                uploadProgressPercent.textContent =
                    uploadPercent + "%";

                if (uploadPercent < 30) {

                    uploadProgressText.textContent =
                        "Uploading file...";

                } else if (uploadPercent < 80) {

                    uploadProgressText.textContent =
                        "Securing your file...";

                } else if (uploadPercent < 100) {

                    uploadProgressText.textContent =
                        "Almost complete...";

                } else {

                    uploadProgressText.textContent =
                        "Processing file...";

                }

            }
        );

        /* ===== UPLOAD PROGRESS EVENT END ===== */


        /* ===== UPLOAD SUCCESS RESPONSE START ===== */

        request.addEventListener(
            "load",
            function () {

                activeUploadRequest = null;


                let result;


                try {

                    result = JSON.parse(
                        request.responseText
                    );

                } catch (error) {

                    showToast(
                        "error",
                        "Invalid server response",
                        "The server returned an unexpected response."
                    );

                    resetUploadProgress(
                        originalButtonContent
                    );

                    return;

                }

                if (
                    request.status < 200
                    ||
                    request.status >= 300
                ) {

                    showToast(
                        "error",
                        "Upload failed",
                        result.message
                        ||
                        "The file could not be uploaded."
                    );

                    resetUploadProgress(
                        originalButtonContent
                    );

                    return;

                }

                uploadProgressBar.style.width =
                    "100%";

                uploadProgressPercent.textContent =
                    "100%";

                uploadProgressText.textContent =
                    "Upload completed successfully.";

                showToast(
                    "success",
                    "Upload complete",
                    "Your file was uploaded securely."
                );

                setTimeout(
                    function () {

                        showUploadSuccess(
                            result
                        );

                        resetUploadForm();

                        resetUploadProgress(
                            originalButtonContent
                        );

                    },
                    500
                );

            }
        );

        /* ===== UPLOAD SUCCESS RESPONSE END ===== */


        /* ===== UPLOAD CONNECTION ERROR START ===== */

        request.addEventListener(
            "error",
            function () {

                activeUploadRequest = null;

                showToast(
                    "error",
                    "Connection failed",
                    "Could not connect to the QuickVault server."
                );

                resetUploadProgress(
                    originalButtonContent
                );

            }
        );

        /* ===== UPLOAD CONNECTION ERROR END ===== */


        /* ===== UPLOAD TIMEOUT START ===== */

        request.addEventListener(
            "timeout",
            function () {

                activeUploadRequest = null;

                showToast(
                    "warning",
                    "Upload timed out",
                    "The upload took too long. Please try again."
                );

                resetUploadProgress(
                    originalButtonContent
                );

            }
        );

        /* ===== UPLOAD TIMEOUT END ===== */


        request.open(
            "POST",
            "/upload"
        );

        request.timeout =
            120000;

        request.send(
            formData
        );

    }
);

/* ========================================================= */
/* ===== 09. REAL FILE UPLOAD WITH PROGRESS END ===== */
/* ========================================================= */

/* ===== 09A. EXPIRY COUNTDOWN START ===== */

function startExpiryCountdown(expiresAtIso) {

    if (expiryCountdownInterval) {

        clearInterval(
            expiryCountdownInterval
        );

    }

    const expiryTime =
        new Date(expiresAtIso).getTime();

    function updateCountdown() {

        const currentTime =
            new Date().getTime();

        const remainingTime =
            expiryTime - currentTime;

        if (remainingTime <= 0) {

            clearInterval(
                expiryCountdownInterval
            );

            expiryCountdown.textContent =
                "EXPIRED";

            expiryCountdown.classList.add(
                "expiry-finished"
            );

            return;

        }

        const hours = Math.floor(
            remainingTime
            /
            (1000 * 60 * 60)
        );

        const minutes = Math.floor(
            (
                remainingTime
                %
                (1000 * 60 * 60)
            )
            /
            (1000 * 60)
        );

        const seconds = Math.floor(
            (
                remainingTime
                %
                (1000 * 60)
            )
            /
            1000
        );

        expiryCountdown.textContent =
            String(hours).padStart(2, "0")
            +
            ":"
            +
            String(minutes).padStart(2, "0")
            +
            ":"
            +
            String(seconds).padStart(2, "0");

    }

    expiryCountdown.classList.remove(
        "expiry-finished"
    );

    updateCountdown();

    expiryCountdownInterval =
        setInterval(
            updateCountdown,
            1000
        );

}

/* ===== 09A. EXPIRY COUNTDOWN END ===== */

/* ===== 09A. RESET UPLOAD PROGRESS START ===== */

function resetUploadProgress(
    originalButtonContent
) {

    secureUploadButton.disabled =
        false;

    secureUploadButton.innerHTML =
        originalButtonContent;

    setTimeout(
        function () {

            uploadProgressWrapper.classList.remove(
                "show"
            );

            uploadProgressBar.style.width =
                "0%";

            uploadProgressPercent.textContent =
                "0%";

            uploadProgressText.textContent =
                "Uploading file...";

        },
        600
    );

}

/* ===== 09A. RESET UPLOAD PROGRESS END ===== */

/* ===== 10. SHOW SUCCESS MODAL START ===== */

function showUploadSuccess(result) {

    latestAccessCode =
        result.access_code;

    successAccessCode.textContent =
        result.access_code;

    successFileName.textContent =
        result.filename;

    successFileSize.textContent =
        formatFileSize(
            result.file_size
        );

    successPinStatus.textContent =
        result.pin_required
        ? "Enabled"
        : "Not enabled";

    successExpiry.textContent =
        result.expires_at;

    successDownloadType.textContent =
        result.one_time_download
        ? "One-time"
        : "Until expiry";
            /* ===== SUCCESS QR DISPLAY START ===== */

    successQrCode.src =
        result.qr_code;

    successQrCode.alt =
        "QR code for access code "
        +
        result.access_code;

    /* ===== SUCCESS QR DISPLAY END ===== */


    /* ===== SUCCESS COUNTDOWN START ===== */

    startExpiryCountdown(
        result.expires_at_iso
    );

    /* ===== SUCCESS COUNTDOWN END ===== */

    copyStatusMessage.textContent =
        "";

    successModal.classList.add(
        "show"
    );

    document.body.style.overflow =
        "hidden";

}

/* ===== 10. SHOW SUCCESS MODAL END ===== */


/* ===== 11. CLOSE SUCCESS MODAL START ===== */

function closeSuccessModal() {

    successModal.classList.remove(
        "show"
    );

    document.body.style.overflow =
        "";

}


closeSuccessButton.addEventListener(
    "click",
    closeSuccessModal
);


successModal.addEventListener(
    "click",
    function (event) {

        if (
            event.target
            ===
            successModal
        ) {

            closeSuccessModal();

        }

    }
);

/* ===== 11. CLOSE SUCCESS MODAL END ===== */


/* ===== 12. COPY ACCESS CODE START ===== */

copyCodeButton.addEventListener(
    "click",
    async function () {

        try {

            await navigator.clipboard.writeText(
                latestAccessCode
            );

            copyStatusMessage.textContent =
                "Access code copied successfully.";

            copyCodeButton.textContent =
                "Copied";

            setTimeout(
                function () {

                    copyCodeButton.textContent =
                        "Copy";

                    copyStatusMessage.textContent =
                        "";

                },
                2000
            );

        } catch (error) {

            console.error(error);

            copyStatusMessage.textContent =
                "Could not copy automatically.";

        }

    }
);

/* ===== 12. COPY ACCESS CODE END ===== */


/* ===== 13. UPLOAD ANOTHER FILE START ===== */

uploadAnotherButton.addEventListener(
    "click",
    function () {

        closeSuccessModal();

        document
            .getElementById("upload")
            .scrollIntoView(
                {
                    behavior:"smooth"
                }
            );

    }
);

/* ===== 13. UPLOAD ANOTHER FILE END ===== */


/* ===== 14. DOWNLOAD NOW BUTTON START ===== */

downloadNowButton.addEventListener(
    "click",
    function () {

        closeSuccessModal();

        document.getElementById(
            "accessCode"
        ).value = latestAccessCode;

        downloadModal.classList.add(
            "show"
        );

        document.body.style.overflow =
            "hidden";

    }
);

/* ===== 14. DOWNLOAD NOW BUTTON END ===== */


/* ===== 15. RESET UPLOAD FORM START ===== */

function resetUploadForm() {

    uploadForm.reset();

    resetSelectedFileDisplay();

}

/* ===== 15. RESET UPLOAD FORM END ===== */


/* ===== 16. DOWNLOAD MODAL OPEN START ===== */

openDownloadButton.addEventListener(
    "click",
    function () {

        downloadModal.classList.add(
            "show"
        );

        document.body.style.overflow =
            "hidden";

    }
);

/* ===== 16. DOWNLOAD MODAL OPEN END ===== */


/* ===== 17. DOWNLOAD MODAL CLOSE START ===== */

function closeDownloadModal() {

    downloadModal.classList.remove(
        "show"
    );

    document.body.style.overflow =
        "";

}


closeDownloadButton.addEventListener(
    "click",
    closeDownloadModal
);


downloadModal.addEventListener(
    "click",
    function (event) {

        if (
            event.target
            ===
            downloadModal
        ) {

            closeDownloadModal();

        }

    }
);

/* ===== 17. DOWNLOAD MODAL CLOSE END ===== */


/* ===== 18. ESCAPE KEY CLOSE START ===== */

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Escape"
        ) {

            closeSuccessModal();

            closeDownloadModal();

        }

    }
);

/* ===== 18. ESCAPE KEY CLOSE END ===== */


/* ========================================================= */
/* ===== 19. REAL FILE ACCESS AND VERIFICATION START ===== */
/* ========================================================= */

downloadForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        const accessCode =
            document.getElementById(
                "accessCode"
            ).value.trim();

        const downloadPin =
            document.getElementById(
                "downloadPin"
            ).value.trim();

        if (
            !/^[0-9]{6}$/.test(
                accessCode
            )
        ) {

            showToast(
                "error",
                "Invalid access code",
                "Enter a valid 6-digit access code."
            );

            return;

        }

        if (
            downloadPin !== ""
            &&
            !/^[0-9]{4}$/.test(
                downloadPin
            )
        ) {

            showToast(
                "error",
                "Invalid PIN",
                "PIN must contain exactly 4 digits."
            );

            return;

        }

        const accessButton =
            downloadForm.querySelector(
                ".access-file-button"
            );

        const originalButtonText =
            accessButton.textContent;

        accessButton.disabled = true;

        accessButton.textContent =
            "Checking File...";

        try {

            const response =
                await fetch(
                    "/access-file",
                    {
                        method:"POST",

                        headers:{
                            "Content-Type":
                                "application/json"
                        },

                        body:JSON.stringify(
                            {
                                access_code:
                                    accessCode,

                                pin:
                                    downloadPin
                            }
                        )
                    }
                );

            const result =
                await response.json();

            if (!response.ok) {

                let messageType = "error";

                if (response.status === 429) {

                    messageType = "warning";

                }

                showToast(
                    messageType,
                    "File access failed",
                    result.message
                    ||
                    "Unable to access this file."
                );

                return;

            }

            closeDownloadModal();

            downloadForm.reset();

            showFileReadyModal(
                result
            );

        } catch (error) {

            console.error(error);

            showToast(
                "error",
                "Connection failed",
                "Could not connect to the QuickVault server."
            );

        } finally {

            accessButton.disabled =
                false;

            accessButton.textContent =
                originalButtonText;

        }

    }
);

/* ========================================================= */
/* ===== 19. REAL FILE ACCESS AND VERIFICATION END ===== */
/* ========================================================= */

/* ===== 20. URL ACCESS CODE AUTO FILL START ===== */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const urlParameters =
            new URLSearchParams(
                window.location.search
            );

        const accessCodeFromUrl =
            urlParameters.get("code");

        if (
            accessCodeFromUrl
            &&
            /^[0-9]{6}$/.test(
                accessCodeFromUrl
            )
        ) {

            document.getElementById(
                "accessCode"
            ).value =
                accessCodeFromUrl;

            downloadModal.classList.add(
                "show"
            );

            document.body.style.overflow =
                "hidden";

        }

    }
);

/* ===== 20. URL ACCESS CODE AUTO FILL END ===== */

/* ========================================================= */
/* ===== 20. PROFESSIONAL TOAST SYSTEM START ===== */
/* ========================================================= */

const toastNotification =
    document.getElementById(
        "toastNotification"
    );

const toastIcon =
    document.getElementById(
        "toastIcon"
    );

const toastTitle =
    document.getElementById(
        "toastTitle"
    );

const toastMessage =
    document.getElementById(
        "toastMessage"
    );

const toastCloseButton =
    document.getElementById(
        "toastCloseButton"
    );

let toastTimer = null;


function showToast(
    type,
    title,
    message
) {

    clearTimeout(toastTimer);

    toastNotification.classList.remove(
        "toast-success",
        "toast-error",
        "toast-warning"
    );

    if (type === "error") {

        toastNotification.classList.add(
            "toast-error"
        );

        toastIcon.textContent = "!";

    } else if (type === "warning") {

        toastNotification.classList.add(
            "toast-warning"
        );

        toastIcon.textContent = "⚠";

    } else {

        toastNotification.classList.add(
            "toast-success"
        );

        toastIcon.textContent = "✓";

    }

    toastTitle.textContent = title;

    toastMessage.textContent = message;

    toastNotification.classList.add(
        "show"
    );

    toastTimer = setTimeout(
        function () {

            closeToast();

        },
        4500
    );

}


function closeToast() {

    toastNotification.classList.remove(
        "show"
    );

}


toastCloseButton.addEventListener(
    "click",
    closeToast
);

/* ========================================================= */
/* ===== 20. PROFESSIONAL TOAST SYSTEM END ===== */
/* ========================================================= */


/* ========================================================= */
/* ===== 21. FILE READY MODAL REFERENCES START ===== */
/* ========================================================= */

const fileReadyModal =
    document.getElementById(
        "fileReadyModal"
    );

const fileReadyCloseButton =
    document.getElementById(
        "fileReadyCloseButton"
    );

const readyFileName =
    document.getElementById(
        "readyFileName"
    );

const readyFileSize =
    document.getElementById(
        "readyFileSize"
    );

const readyFileExpiry =
    document.getElementById(
        "readyFileExpiry"
    );

const readyDownloadType =
    document.getElementById(
        "readyDownloadType"
    );

const fileReadyWarning =
    document.getElementById(
        "fileReadyWarning"
    );

const finalDownloadButton =
    document.getElementById(
        "finalDownloadButton"
    );

let verifiedDownloadUrl = "";

/* ========================================================= */
/* ===== 21. FILE READY MODAL REFERENCES END ===== */
/* ========================================================= */


/* ========================================================= */
/* ===== 22. FILE READY MODAL FUNCTIONS START ===== */
/* ========================================================= */

function showFileReadyModal(result) {

    verifiedDownloadUrl =
        result.download_url;

    readyFileName.textContent =
        result.filename;

    readyFileSize.textContent =
        formatFileSize(
            result.file_size
        );

    const expiryDate =
        new Date(
            result.expires_at
        );

    readyFileExpiry.textContent =
        expiryDate.toLocaleString();

    readyDownloadType.textContent =
        result.one_time_download
        ? "One-time download"
        : "Available until expiry";

    if (result.one_time_download) {

        fileReadyWarning.classList.add(
            "show"
        );

    } else {

        fileReadyWarning.classList.remove(
            "show"
        );

    }

    fileReadyModal.classList.add(
        "show"
    );

    document.body.style.overflow =
        "hidden";

}


function closeFileReadyModal() {

    fileReadyModal.classList.remove(
        "show"
    );

    document.body.style.overflow =
        "";

}


fileReadyCloseButton.addEventListener(
    "click",
    closeFileReadyModal
);


fileReadyModal.addEventListener(
    "click",
    function (event) {

        if (
            event.target
            ===
            fileReadyModal
        ) {

            closeFileReadyModal();

        }

    }
);


finalDownloadButton.addEventListener(
    "click",
    function () {

        if (!verifiedDownloadUrl) {

            showToast(
                "error",
                "Download unavailable",
                "Please verify the file again."
            );

            return;

        }

        closeFileReadyModal();

        showToast(
            "success",
            "Download started",
            "Your file download has started."
        );

        window.location.href =
            verifiedDownloadUrl;

        verifiedDownloadUrl = "";

    }
);

/* ========================================================= */
/* ===== 22. FILE READY MODAL FUNCTIONS END ===== */
/* ========================================================= */

/* ========================================================= */
/* ===== 23. CANCEL ACTIVE UPLOAD START ===== */
/* ========================================================= */

cancelUploadButton.addEventListener(
    "click",
    function () {

        if (!activeUploadRequest) {

            showToast(
                "warning",
                "No active upload",
                "There is no upload to cancel."
            );

            return;

        }

        activeUploadRequest.abort();

        activeUploadRequest = null;

        uploadProgressWrapper.classList.remove(
            "show"
        );

        uploadProgressBar.style.width =
            "0%";

        uploadProgressPercent.textContent =
            "0%";

        uploadProgressText.textContent =
            "Upload cancelled.";

        secureUploadButton.disabled =
            false;

        secureUploadButton.innerHTML =
            `
            <span>🔒</span>
            Upload Securely
            `;

        showToast(
            "warning",
            "Upload cancelled",
            "The file upload was cancelled."
        );

    }
);

/* ========================================================= */
/* ===== 23. CANCEL ACTIVE UPLOAD END ===== */
/* ========================================================= */
