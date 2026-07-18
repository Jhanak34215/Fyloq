/* =========================================================
   FYLOQ VIEW + PRINT JAVASCRIPT
   File: static/js/view_print.js
   ========================================================= */


const printFileButton =
    document.getElementById(
        "printFileButton"
    );


const viewerLoading =
    document.getElementById(
        "viewerLoading"
    );


const viewerError =
    document.getElementById(
        "viewerError"
    );


const viewerErrorMessage =
    document.getElementById(
        "viewerErrorMessage"
    );


const secureDocumentViewer =
    document.getElementById(
        "secureDocumentViewer"
    );


const secureImageViewer =
    document.getElementById(
        "secureImageViewer"
    );


const viewerToast =
    document.getElementById(
        "viewerToast"
    );


const viewerToastIcon =
    document.getElementById(
        "viewerToastIcon"
    );


const viewerToastMessage =
    document.getElementById(
        "viewerToastMessage"
    );


const fileType =
    document.body.dataset.fileType;


let viewerToastTimer = null;


/* =========================================================
   TOAST START
   ========================================================= */

function showViewerToast(
    type,
    message
) {

    clearTimeout(
        viewerToastTimer
    );

    viewerToast.classList.remove(
        "error"
    );

    if (type === "error") {

        viewerToast.classList.add(
            "error"
        );

        viewerToastIcon.textContent =
            "!";

    } else {

        viewerToastIcon.textContent =
            "✓";

    }

    viewerToastMessage.textContent =
        message;

    viewerToast.classList.add(
        "show"
    );

    viewerToastTimer =
        setTimeout(
            function () {

                viewerToast.classList.remove(
                    "show"
                );

            },
            3500
        );

}

/* =========================================================
   TOAST END
   ========================================================= */


/* =========================================================
   VIEWER LOAD HANDLING START
   ========================================================= */

function hideViewerLoading() {

    viewerLoading.classList.add(
        "hide"
    );

}


function showViewerError(message) {

    hideViewerLoading();

    viewerErrorMessage.textContent =
        message;

    viewerError.hidden =
        false;

    printFileButton.disabled =
        true;

}


if (secureDocumentViewer) {

    secureDocumentViewer.addEventListener(
        "load",
        function () {

            hideViewerLoading();

        }
    );

    secureDocumentViewer.addEventListener(
        "error",
        function () {

            showViewerError(
                "The PDF could not be displayed."
            );

        }
    );

}


if (secureImageViewer) {

    secureImageViewer.addEventListener(
        "load",
        function () {

            hideViewerLoading();

        }
    );

    secureImageViewer.addEventListener(
        "error",
        function () {

            showViewerError(
                "The image could not be displayed."
            );

        }
    );

}

/* =========================================================
   VIEWER LOAD HANDLING END
   ========================================================= */


/* =========================================================
   PRINT FILE START
   ========================================================= */

printFileButton.addEventListener(
    "click",
    function () {

        printFileButton.disabled =
            true;

        printFileButton.innerHTML =
            `
                <span>⏳</span>
                Preparing...
            `;

        showViewerToast(
            "success",
            "Preparing the file for printing."
        );

        setTimeout(
            function () {

                if (
                    fileType === "pdf"
                    &&
                    secureDocumentViewer
                ) {

                    try {

                        secureDocumentViewer
                            .contentWindow
                            .focus();

                        secureDocumentViewer
                            .contentWindow
                            .print();

                    } catch (error) {

                        window.print();

                    }

                } else {

                    window.print();

                }

                printFileButton.disabled =
                    false;

                printFileButton.innerHTML =
                    `
                        <span>🖨️</span>
                        Print File
                    `;

            },
            500
        );

    }
);

/* =========================================================
   PRINT FILE END
   ========================================================= */


/* =========================================================
   BASIC DOWNLOAD SHORTCUT PROTECTION START
   ========================================================= */

document.addEventListener(
    "contextmenu",
    function (event) {

        event.preventDefault();

        showViewerToast(
            "error",
            "Right-click is disabled in secure view mode."
        );

    }
);


document.addEventListener(
    "keydown",
    function (event) {

        const pressedKey =
            event.key.toLowerCase();

        const saveShortcut =
            (
                event.ctrlKey
                ||
                event.metaKey
            )
            &&
            pressedKey === "s";

        const sourceShortcut =
            (
                event.ctrlKey
                ||
                event.metaKey
            )
            &&
            pressedKey === "u";

        const developerShortcut =
            (
                event.ctrlKey
                &&
                event.shiftKey
                &&
                [
                    "i",
                    "j",
                    "c"
                ].includes(
                    pressedKey
                )
            );

        const functionKey =
            event.key === "F12";

        if (
            saveShortcut
            ||
            sourceShortcut
            ||
            developerShortcut
            ||
            functionKey
        ) {

            event.preventDefault();

            showViewerToast(
                "error",
                "This action is disabled in secure view mode."
            );

        }

    }
);


document.addEventListener(
    "dragstart",
    function (event) {

        if (
            event.target.tagName === "IMG"
        ) {

            event.preventDefault();

        }

    }
);

/* =========================================================
   BASIC DOWNLOAD SHORTCUT PROTECTION END
   ========================================================= */