// Initialize storage for mapping history and current mappings
const mappingHistory = new Map();
const currentMappings = new Map();

// Variables to track drag state
let draggedHeader = null;
let dragSource = null;

// Helper function to allow drops
function allowDrop(event) {
  event.preventDefault();
  const dropTarget = event.target.closest('.header-item');
  if (dropTarget) {
    dropTarget.classList.add('drag-over');
  }
}

function handleDragStart(event, source) {
  const header = event.target.dataset.header;
  draggedHeader = header;
  dragSource = source;
  event.target.classList.add('dragging');

  // Add dragging class to all valid drop targets
  const dropTargets = document.querySelectorAll(
    source === 'missing' ? '.extra-headers-list .header-item' : '.missing-headers-list .header-item'
  );
  dropTargets.forEach(target => target.classList.add('valid-drop-target'));
}

function handleDrop(event, targetSource) {
  event.preventDefault();

  if (!draggedHeader || dragSource === targetSource) {
    return;
  }

  const fileSection = event.target.closest('.result-section');
  const fileId = fileSection.dataset.fileId;

  const targetHeader = event.target.closest('.header-item')?.dataset.header;
  if (!targetHeader) return;

  // Save current state to history
  if (!mappingHistory.has(fileId)) {
    mappingHistory.set(fileId, []);
  }
  const currentState = {
    missing: [...fileSection.querySelectorAll('.missing-headers-list .header-item')].map(el => el.dataset.header),
    extra: [...fileSection.querySelectorAll('.extra-headers-list .header-item')].map(el => el.dataset.header),
    matched: [...fileSection.querySelectorAll('.matched-headers-list li')]
      .map(el => ({
        text: el.textContent.trim(),
        isNew: el.querySelector('.badge') !== null
      }))
  };
  mappingHistory.get(fileId).push(currentState);

  // Create the new mapping (Extra → Missing)
  const extraHeader = dragSource === 'extra' ? draggedHeader : targetHeader;
  const missingHeader = dragSource === 'extra' ? targetHeader : draggedHeader;

  // Add to current mappings
  if (!currentMappings.has(fileId)) {
    currentMappings.set(fileId, new Map());
  }
  currentMappings.get(fileId).set(extraHeader, missingHeader);

  // Create new matched header element
  const matchedList = fileSection.querySelector('.matched-headers-list');
  const newMatchedItem = document.createElement('li');
  newMatchedItem.className = 'py-1 px-2 mb-2 bg-white rounded border';
  newMatchedItem.innerHTML = `
    <span class="badge bg-primary me-2">New</span>
    <i class="bi bi-check-circle text-success me-2"></i>
    ${extraHeader} → ${missingHeader}
  `;
  matchedList.appendChild(newMatchedItem);

  // Remove the mapped headers from their original lists
  const draggedElement = fileSection.querySelector(`[data-header="${draggedHeader}"]`);
  const targetElement = fileSection.querySelector(`[data-header="${targetHeader}"]`);
  draggedElement.remove();
  targetElement.remove();

  // Show the undo button
  fileSection.querySelector('.undo-btn').classList.remove('d-none');

  // Reset drag state
  draggedHeader = null;
  dragSource = null;

  // Remove any lingering drag-related classes
  document.querySelectorAll('.drag-over, .valid-drop-target').forEach(el => {
    el.classList.remove('drag-over', 'valid-drop-target');
  });
}

function handleDragEnd(event) {
  event.target.classList.remove('dragging');
  // Remove drag-over and valid-drop-target classes
  document.querySelectorAll('.drag-over, .valid-drop-target').forEach(el => {
    el.classList.remove('drag-over', 'valid-drop-target');
  });
}

function handleUndo(fileId) {
  const fileSection = document.querySelector(`.result-section[data-file-id="${fileId}"]`);
  const history = mappingHistory.get(fileId);

  if (!history || history.length === 0) return;

  // Get the previous state
  const previousState = history.pop();

  // Restore the lists
  const missingList = fileSection.querySelector('.missing-headers-list');
  const extraList = fileSection.querySelector('.extra-headers-list');
  const matchedList = fileSection.querySelector('.matched-headers-list');

  // Clear current lists
  missingList.innerHTML = '';
  extraList.innerHTML = '';
  matchedList.innerHTML = '';

  // Restore missing headers
  previousState.missing.forEach(header => {
    const li = document.createElement('li');
    li.className = 'py-1 px-2 mb-2 bg-white rounded border header-item';
    li.draggable = true;
    li.dataset.header = header;
    li.innerHTML = `
      <i class="bi bi-arrows-move me-2 text-muted"></i>
      ${header}
    `;
    li.addEventListener('dragstart', (e) => handleDragStart(e, 'missing'));
    missingList.appendChild(li);
  });

  // Restore extra headers
  previousState.extra.forEach(header => {
    const li = document.createElement('li');
    li.className = 'py-1 px-2 mb-2 bg-white rounded border header-item';
    li.draggable = true;
    li.dataset.header = header;
    li.innerHTML = `
      <i class="bi bi-arrows-move me-2 text-muted"></i>
      ${header}
    `;
    li.addEventListener('dragstart', (e) => handleDragStart(e, 'extra'));
    extraList.appendChild(li);
  });

  // Restore matched headers with their New badges
  previousState.matched.forEach(header => {
    const li = document.createElement('li');
    li.className = 'py-1 px-2 mb-2 bg-white rounded border';
    li.innerHTML = `
      ${header.isNew ? '<span class="badge bg-primary me-2">New</span>' : ''}
      <i class="bi bi-check-circle text-success me-2"></i>
      ${header.text}
    `;
    matchedList.appendChild(li);
  });

  // Remove the last mapping from currentMappings
  const mappings = currentMappings.get(fileId);
  if (mappings && mappings.size > 0) {
    const lastKey = Array.from(mappings.keys()).pop();
    mappings.delete(lastKey);
  }

  // Hide undo button if no more history
  if (history.length === 0) {
    fileSection.querySelector('.undo-btn').classList.add('d-none');
  }
}

function handleDownload(fileId, filename) {
  const button = document.querySelector(`button[data-file-id="${fileId}"]`);
  if (!button) return;

  const spinner = button.querySelector('.spinner-border');
  const toast = new bootstrap.Toast(document.getElementById('errorToast'));

  // Get custom mappings for this file
  const mappings = Object.fromEntries(currentMappings.get(fileId) || []);

  // Disable button and show spinner
  button.disabled = true;
  spinner.classList.remove('d-none');

  fetch(`/merge_and_download/${fileId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ mappings })
  })
    .then(response => {
      if (!response.ok) {
        return response.text().then(errorMsg => {
          throw new Error(errorMsg || 'Download failed. Please try again.');
        });
      }
      return response.blob();
    })
    .then(blob => {
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
      const toastBody = document.querySelector('#errorToast .toast-body');
      toastBody.textContent = error.message;
      toast.show();
    })
    .finally(() => {
      button.disabled = false;
      spinner.classList.add('d-none');
    });
}

// Initialize drag and drop event listeners
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.header-item').forEach(item => {
    item.addEventListener('dragend', handleDragEnd);
    item.addEventListener('dragleave', (e) => {
      e.target.closest('.header-item')?.classList.remove('drag-over');
    });
  });
});