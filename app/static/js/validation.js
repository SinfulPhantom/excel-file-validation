function downloadFile(fileId, filename) {
  const button = document.querySelector(`button[data-file-id="${fileId}"]`);
  const spinner = button.querySelector('.spinner-border');

  spinner.classList.remove('d-none');
  button.disabled = true;

  fetch(`/merge_and_download/${fileId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const originalName = filename.split('.')[0];
      a.download = `${originalName}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    })
    .catch(error => {
      console.error('Error:', error);
      showToast('Error downloading file. Please try again.');
    })
    .finally(() => {
      spinner.classList.add('d-none');
      button.disabled = false;
    });
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'alert alert-danger alert-dismissible fade show position-fixed bottom-0 end-0 m-3';
  toast.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}