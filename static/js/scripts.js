document.addEventListener('DOMContentLoaded', function () {
    let uploadArea = document.getElementById('uploadfile');
    let fileInput = document.getElementById('file');

    uploadArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function (e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function (e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
        let files = e.dataTransfer.files;
        fileInput.files = files;
    });
});

