function handleDownload(fileId, filename) {
  const button = document.querySelector(`button[data-file-id="${fileId}"]`);
  if (!button) return;

  const spinner = button.querySelector('.spinner-border');
  const toast = new bootstrap.Toast(document.getElementById('errorToast'));

  // Disable button and show spinner
  button.disabled = true;
  spinner.classList.remove('d-none');

  fetch(`/merge_and_download/${fileId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Download failed. Please try again.');
      }
      return response.blob();
    })
    .then(blob => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename.replace(/\.[^/.]+$/, '.csv');
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    })
    .catch(error => {
      // Show error toast
      const toastBody = document.querySelector('#errorToast .toast-body');
      toastBody.textContent = error.message;
      toast.show();
    })
    .finally(() => {
      // Reset button state
      button.disabled = false;
      spinner.classList.add('d-none');
    });
}