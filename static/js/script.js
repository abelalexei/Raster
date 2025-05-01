// Script para mostrar el nombre de los archivos seleccionados
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    const fileNameDisplay = document.getElementById('file-name-display');
    
    if (fileInput && fileNameDisplay) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                if (fileInput.files.length === 1) {
                    fileNameDisplay.textContent = fileInput.files[0].name;
                } else {
                    const fileCount = fileInput.files.length;
                    const fileNames = Array.from(fileInput.files)
                        .slice(0, 3)
                        .map(file => file.name)
                        .join(', ');
                    
                    if (fileCount > 3) {
                        fileNameDisplay.textContent = `${fileNames} y ${fileCount - 3} más`;
                    } else {
                        fileNameDisplay.textContent = fileNames;
                    }
                }
            } else {
                fileNameDisplay.textContent = 'Ningún archivo seleccionado';
            }
        });
    }
});