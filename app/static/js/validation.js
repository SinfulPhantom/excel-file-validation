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
  
  const draggedHeader = event.dataTransfer.getData('text/plain');
  const draggedSource = event.dataTransfer.getData('source');
  const fileId = event.target.closest('.result-section').dataset.fileId;
  
  // Don't allow dropping on the same list
  if (draggedSource === targetSource) return;
  
  // Find the lists
  const resultSection = event.target.closest('.result-section');
  const sourceList = resultSection.querySelector(`.${draggedSource}-headers-list`);
  const targetList = resultSection.querySelector(`.${targetSource}-headers-list`);
  const matchedList = resultSection.querySelector('.matched-headers-list');
  
  // Remove the dragged item from source list
  const draggedItem = sourceList.querySelector(`[data-header="${draggedHeader}"]`);
  if (!draggedItem) return;
  draggedItem.remove();
  
  // Remove the target item if dropping on a specific header
  let targetHeader = '';
  const dropTarget = event.target.closest('.header-item');
  if (dropTarget) {
      targetHeader = dropTarget.dataset.header;
      dropTarget.remove();
  }
  
  // Determine which header is from extra and which is from missing
  let extraHeader, missingHeader;
  if (draggedSource === 'extra') {
      extraHeader = draggedHeader;
      missingHeader = targetHeader;
  } else {
      extraHeader = targetHeader;
      missingHeader = draggedHeader;
  }
  
  // Create new matched header item
  const matchedItem = document.createElement('li');
  matchedItem.className = 'py-1 px-2 mb-2 bg-white rounded border';
  matchedItem.innerHTML = `
      <i class="bi bi-check-circle text-success me-2"></i>
      <span class="badge bg-primary me-2">New</span>
      ${extraHeader} → ${missingHeader}
  `;
  
  // Store the mapping information (extra header -> missing header)
  matchedItem.setAttribute('data-source-header', extraHeader);
  matchedItem.setAttribute('data-target-header', missingHeader);
  
  // Add to matched headers
  if (matchedList.querySelector('.text-muted')) {
      matchedList.innerHTML = ''; // Remove "No matched headers" message
  }
  matchedList.appendChild(matchedItem);
  
  // Show undo button
  const undoButton = resultSection.querySelector('.undo-btn');
  if (undoButton) {
      undoButton.classList.remove('d-none');
  }
  
  // Add to mapping history
  if (!mappingHistory.has(fileId)) {
      mappingHistory.set(fileId, []);
  }
  mappingHistory.get(fileId).push({
      sourceList: draggedSource,
      targetList: targetSource,
      sourceHeader: draggedHeader,
      targetHeader: targetHeader,
      matchedItem: matchedItem.cloneNode(true)
  });
  
  // Update current mappings (store extra header -> missing header)
  if (!currentMappings.has(fileId)) {
      currentMappings.set(fileId, new Map());
  }
  currentMappings.get(fileId).set(extraHeader, missingHeader);
  
  // Add empty state message if source list is empty
  if (!sourceList.children.length) {
      sourceList.innerHTML = '<li class="text-muted">No extra headers</li>';
  }
  if (!targetList.children.length) {
      targetList.innerHTML = '<li class="text-muted">No missing headers</li>';
  }
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

  // Disable button and show spinner
  button.disabled = true;
  if (spinner) spinner.classList.remove('d-none');

  // Get current mappings from the UI state
  const mappings = {};
  const resultSection = button.closest('.result-section');
  const matchedHeadersList = resultSection.querySelector('.matched-headers-list');
  const matchedHeaders = matchedHeadersList.querySelectorAll('li:not(.text-muted)');
  
  matchedHeaders.forEach(header => {
      // Extract the source (extra) and target (missing) headers from the data attributes
      const sourceHeader = header.getAttribute('data-source-header');
      const targetHeader = header.getAttribute('data-target-header');
      if (sourceHeader && targetHeader) {
          // The mapping should be from extra header to missing header
          mappings[sourceHeader] = targetHeader;
      }
  });

  fetch(`/merge_and_download/${fileId}`, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({ mappings: mappings })
  })
      .then(response => {
          if (!response.ok) {
              return response.text().then(text => {
                  throw new Error(text || 'Download failed. Please try again.');
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
          alert(error.message);
      })
      .finally(() => {
          button.disabled = false;
          if (spinner) spinner.classList.add('d-none');
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