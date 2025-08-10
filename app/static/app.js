/**
 * AI Sales Agent Frontend JavaScript
 * Handles file upload, progress tracking, and UI interactions
 */

// Global configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    MAX_FILE_SIZE_MB: 10,
    POLL_INTERVAL_MS: 2000,
    MAX_RETRIES: 3,
    RETRY_DELAY_MS: 1000
};

// Global state
let currentJobId = null;
let pollInterval = null;
let uploadInProgress = false;

/**
 * Initialize the application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeUploadPage();
    setupGlobalErrorHandler();
});

/**
 * Initialize upload page functionality
 */
function initializeUploadPage() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const removeFileBtn = document.getElementById('removeFile');

    if (!uploadArea || !fileInput || !uploadBtn) {
        // Not on upload page
        return;
    }

    // File selection handlers
    setupFileUploadHandlers(uploadArea, fileInput, uploadBtn, removeFileBtn);
    
    // Upload button handler
    uploadBtn.addEventListener('click', handleUpload);
    
    // Remove file handler
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', clearFileSelection);
    }
}

/**
 * Setup file upload drag-and-drop and click handlers
 */
function setupFileUploadHandlers(uploadArea, fileInput, uploadBtn, removeFileBtn) {
    // Click to browse
    uploadArea.addEventListener('click', function(e) {
        if (e.target.closest('.remove-file')) return;
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleFileSelection(file);
        }
    });

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (validateFile(file)) {
                handleFileSelection(file);
                // Update file input
                const dt = new DataTransfer();
                dt.items.add(file);
                fileInput.files = dt.files;
            }
        }
    });
}

/**
 * Handle file selection and validation
 */
function handleFileSelection(file) {
    if (!validateFile(file)) {
        return;
    }

    const uploadArea = document.getElementById('uploadArea');
    const filePreview = document.getElementById('filePreview');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');

    // Update UI to show selected file
    if (filePreview && fileName && fileSize) {
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        
        uploadArea.style.display = 'none';
        filePreview.style.display = 'block';
    } else {
        // Fallback for simpler UI
        uploadArea.innerHTML = `
            <div class="upload-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14,2 L6,2 C4.9,2 4,2.9 4,4 L4,20 C4,21.1 4.9,22 6,22 L18,22 C19.1,22 20,21.1 20,20 L20,8 L14,2 Z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
            </div>
            <h3>${file.name}</h3>
            <p>${formatFileSize(file.size)}</p>
            <p class="upload-link" onclick="clearFileSelection()">Choose different file</p>
        `;
    }

    uploadBtn.disabled = false;
}

/**
 * Validate selected file
 */
function validateFile(file) {
    const errors = [];

    // Check file type
    if (!file.name.toLowerCase().endsWith('.csv')) {
        errors.push('Please select a CSV file');
    }

    // Check file size
    const maxSizeBytes = CONFIG.MAX_FILE_SIZE_MB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
        errors.push(`File size must be less than ${CONFIG.MAX_FILE_SIZE_MB}MB`);
    }

    // Check if file is empty
    if (file.size === 0) {
        errors.push('File appears to be empty');
    }

    if (errors.length > 0) {
        showAlert(errors.join('. '), 'error');
        return false;
    }

    return true;
}

/**
 * Clear file selection and reset UI
 */
function clearFileSelection() {
    const uploadArea = document.getElementById('uploadArea');
    const filePreview = document.getElementById('filePreview');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');

    if (filePreview) {
        uploadArea.style.display = 'block';
        filePreview.style.display = 'none';
    } else {
        // Reset upload area HTML
        uploadArea.innerHTML = `
            <div class="upload-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
            </div>
            <h3>Drop your CSV here</h3>
            <p>or <span class="upload-link">click to browse</span></p>
            <div class="file-requirements">
                <p>• CSV format only</p>
                <p>• Maximum ${CONFIG.MAX_FILE_SIZE_MB}MB file size</p>
                <p>• Required columns: Company Name, Address, Phone</p>
            </div>
        `;
        
        // Re-setup handlers
        initializeUploadPage();
    }

    fileInput.value = '';
    uploadBtn.disabled = true;
}

/**
 * Handle file upload
 */
async function handleUpload() {
    if (uploadInProgress) {
        return;
    }

    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];

    if (!file || !validateFile(file)) {
        showAlert('Please select a valid CSV file', 'error');
        return;
    }

    uploadInProgress = true;
    const uploadBtn = document.getElementById('uploadBtn');
    const originalText = uploadBtn.querySelector('.btn-text')?.textContent || uploadBtn.textContent;
    
    try {
        // Update button state
        setButtonLoading(uploadBtn, true);
        
        // Show status section
        showStatusSection();
        updateStatus('Uploading file...', 'processing');

        // Create form data
        const formData = new FormData();
        formData.append('file', file);

        // Upload file with progress tracking
        const response = await uploadWithProgress(formData);

        if (response.ok) {
            const data = await response.json();
            currentJobId = data.job_id;
            
            // Update status
            updateStatus(`Job created! Processing ${data.total_records || 0} records...`, 'processing');
            updateJobDetails(data);
            
            // Start polling for status
            startStatusPolling(data.job_id);
            
        } else {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || errorData.message || `Upload failed (${response.status})`);
        }

    } catch (error) {
        console.error('Upload error:', error);
        updateStatus(`Error: ${error.message}`, 'error');
        setButtonLoading(uploadBtn, false, originalText);
        uploadInProgress = false;
    }
}

/**
 * Upload file with progress tracking
 */
function uploadWithProgress(formData) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateProgress(percentComplete, 'Uploading...');
            }
        });

        xhr.addEventListener('load', function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve({
                    ok: true,
                    status: xhr.status,
                    json: () => Promise.resolve(JSON.parse(xhr.responseText))
                });
            } else {
                reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
            }
        });

        xhr.addEventListener('error', function() {
            reject(new Error('Network error occurred'));
        });

        xhr.addEventListener('timeout', function() {
            reject(new Error('Request timeout'));
        });

        xhr.open('POST', `${CONFIG.API_BASE_URL}/api/v1/jobs/upload`);
        xhr.timeout = 60000; // 60 second timeout
        xhr.send(formData);
    });
}

/**
 * Show status section
 */
function showStatusSection() {
    const statusSection = document.getElementById('statusSection');
    if (statusSection) {
        statusSection.style.display = 'block';
    }
}

/**
 * Update status display
 */
function updateStatus(message, type) {
    const statusBadge = document.getElementById('statusBadge');
    const alertMessage = document.getElementById('alertMessage');
    const alertText = document.getElementById('alertText');
    const alertIcon = document.getElementById('alertIcon');

    if (statusBadge) {
        statusBadge.textContent = type === 'processing' ? 'Processing' : 
                                type === 'error' ? 'Error' : 
                                type === 'completed' ? 'Completed' : 'Unknown';
        statusBadge.className = `status-badge ${type}`;
    }

    if (alertMessage && alertText) {
        alertText.textContent = message;
        alertMessage.className = `alert ${type === 'error' ? 'error' : type === 'completed' ? 'success' : 'info'}`;
        alertMessage.style.display = 'block';

        // Auto-hide success/error messages
        if (type === 'completed' || type === 'error') {
            setTimeout(() => {
                alertMessage.style.display = 'none';
            }, 5000);
        }
    }
}

/**
 * Update progress bar
 */
function updateProgress(percentage, details) {
    const progressFill = document.getElementById('progressFill');
    const progressPercentage = document.getElementById('progressPercentage');
    const progressDetails = document.getElementById('progressDetails');

    if (progressFill) {
        progressFill.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
    }

    if (progressPercentage) {
        progressPercentage.textContent = `${Math.round(percentage)}%`;
    }

    if (progressDetails && details) {
        progressDetails.textContent = details;
    }
}

/**
 * Update job details
 */
function updateJobDetails(data) {
    const jobId = document.getElementById('jobId');
    const recordCount = document.getElementById('recordCount');
    const processedCount = document.getElementById('processedCount');
    const estimatedTime = document.getElementById('estimatedTime');

    if (jobId) jobId.textContent = data.job_id || '-';
    if (recordCount) recordCount.textContent = data.total_records || '-';
    if (processedCount) processedCount.textContent = data.processed_records || '0';
    if (estimatedTime) {
        if (data.estimated_completion) {
            const eta = new Date(data.estimated_completion);
            estimatedTime.textContent = eta.toLocaleTimeString();
        } else {
            estimatedTime.textContent = 'Calculating...';
        }
    }
}

/**
 * Start polling job status
 */
function startStatusPolling(jobId) {
    if (pollInterval) {
        clearInterval(pollInterval);
    }

    pollInterval = setInterval(async () => {
        try {
            await pollJobStatus(jobId);
        } catch (error) {
            console.error('Polling error:', error);
            // Don't stop polling on individual errors
        }
    }, CONFIG.POLL_INTERVAL_MS);

    // Initial poll
    pollJobStatus(jobId);
}

/**
 * Poll job status
 */
async function pollJobStatus(jobId) {
    try {
        const response = await fetchWithRetry(`${CONFIG.API_BASE_URL}/api/v1/jobs/${jobId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        handleStatusUpdate(data);

    } catch (error) {
        console.error('Status polling error:', error);
        // Show error but don't stop polling immediately
        if (error.message.includes('404')) {
            updateStatus('Job not found', 'error');
            stopStatusPolling();
        }
    }
}

/**
 * Handle status update from polling
 */
function handleStatusUpdate(data) {
    const status = data.status;
    
    updateJobDetails(data);

    switch (status) {
        case 'pending':
            updateProgress(0, 'Queued for processing...');
            updateStatus('Job is queued', 'processing');
            break;

        case 'processing':
            if (data.progress) {
                const percentage = data.progress.percentage || 0;
                const processed = data.progress.processed_records || 0;
                const total = data.progress.total_records || 0;
                updateProgress(percentage, `Processing: ${processed}/${total} records`);
                updateStatus('Processing records...', 'processing');
            }
            break;

        case 'completed':
            updateProgress(100, 'Enrichment completed successfully!');
            updateStatus('Job completed successfully', 'completed');
            showCompletedActions(data.job_id);
            stopStatusPolling();
            uploadInProgress = false;
            break;

        case 'failed':
            updateStatus(`Job failed: ${data.error || 'Unknown error'}`, 'error');
            stopStatusPolling();
            uploadInProgress = false;
            resetUploadButton();
            break;

        case 'cancelled':
            updateStatus('Job was cancelled', 'error');
            stopStatusPolling();
            uploadInProgress = false;
            resetUploadButton();
            break;

        default:
            updateStatus(`Unknown status: ${status}`, 'error');
            break;
    }
}

/**
 * Show completed actions
 */
function showCompletedActions(jobId) {
    const actionButtons = document.getElementById('actionButtons');
    const downloadBtn = document.getElementById('downloadBtn');
    const viewStatusBtn = document.getElementById('viewStatusBtn');

    if (actionButtons) {
        actionButtons.style.display = 'block';
    }

    if (downloadBtn) {
        downloadBtn.onclick = () => downloadResults(jobId);
    }

    if (viewStatusBtn) {
        viewStatusBtn.onclick = () => {
            window.open(`status.html?job=${jobId}`, '_blank');
        };
    }

    resetUploadButton();
}

/**
 * Download results
 */
function downloadResults(jobId) {
    const link = document.createElement('a');
    link.href = `${CONFIG.API_BASE_URL}/api/v1/jobs/${jobId}/download`;
    link.download = `enriched_${jobId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Stop status polling
 */
function stopStatusPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

/**
 * Reset upload button
 */
function resetUploadButton() {
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) {
        setButtonLoading(uploadBtn, false, 'Start Enrichment');
    }
}

/**
 * Set button loading state
 */
function setButtonLoading(button, loading, originalText = null) {
    const btnText = button.querySelector('.btn-text');
    const spinner = button.querySelector('.spinner');

    if (loading) {
        button.disabled = true;
        if (btnText) btnText.style.display = 'none';
        if (spinner) spinner.style.display = 'inline-block';
        if (!btnText && !spinner) {
            button.innerHTML = '<div class="spinner"></div> Processing...';
        }
    } else {
        button.disabled = false;
        if (btnText) {
            btnText.style.display = 'inline';
            if (originalText) btnText.textContent = originalText;
        }
        if (spinner) spinner.style.display = 'none';
        if (!btnText && originalText) {
            button.textContent = originalText;
        }
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info', duration = 5000) {
    // Try to use existing alert element first
    let alertElement = document.getElementById('alertMessage');
    let alertText = document.getElementById('alertText');
    let alertIcon = document.getElementById('alertIcon');

    if (!alertElement) {
        // Create temporary alert if no existing alert system
        alertElement = createTempAlert(message, type, duration);
        return;
    }

    // Update existing alert
    if (alertText) {
        alertText.textContent = message;
    } else {
        alertElement.textContent = message;
    }

    alertElement.className = `alert ${type}`;
    alertElement.style.display = 'block';

    // Auto-hide
    setTimeout(() => {
        alertElement.style.display = 'none';
    }, duration);
}

/**
 * Create temporary alert for pages without alert system
 */
function createTempAlert(message, type, duration) {
    const alert = document.createElement('div');
    alert.className = `alert ${type}`;
    alert.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        max-width: 400px;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        z-index: 10000;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        font-weight: 500;
    `;

    // Set colors based on type
    const colors = {
        success: { bg: '#d4edda', border: '#c3e6cb', color: '#155724' },
        error: { bg: '#f8d7da', border: '#f5c6cb', color: '#721c24' },
        warning: { bg: '#fff3cd', border: '#ffeaa7', color: '#856404' },
        info: { bg: '#d1ecf1', border: '#bee5eb', color: '#0c5460' }
    };

    const color = colors[type] || colors.info;
    alert.style.backgroundColor = color.bg;
    alert.style.borderLeft = `4px solid ${color.border}`;
    alert.style.color = color.color;
    alert.textContent = message;

    document.body.appendChild(alert);

    // Auto-remove
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, duration);

    return alert;
}

/**
 * Fetch with retry logic
 */
async function fetchWithRetry(url, options = {}, retries = CONFIG.MAX_RETRIES) {
    for (let i = 0; i <= retries; i++) {
        try {
            const response = await fetch(url, {
                ...options,
                timeout: 10000 // 10 second timeout
            });
            return response;
        } catch (error) {
            if (i === retries) {
                throw error;
            }
            
            // Wait before retrying
            await new Promise(resolve => 
                setTimeout(resolve, CONFIG.RETRY_DELAY_MS * Math.pow(2, i))
            );
        }
    }
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format time for display
 */
function formatTime(timestamp) {
    if (!timestamp) return '-';
    
    try {
        const date = new Date(timestamp);
        return date.toLocaleString();
    } catch (error) {
        return '-';
    }
}

/**
 * Setup global error handler
 */
function setupGlobalErrorHandler() {
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        
        // Don't show alerts for network errors during polling
        if (event.error?.message?.includes('Failed to fetch') && pollInterval) {
            return;
        }
        
        showAlert('An unexpected error occurred. Please try refreshing the page.', 'error');
    });

    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        
        // Don't show alerts for network errors during polling
        if (event.reason?.message?.includes('Failed to fetch') && pollInterval) {
            return;
        }
        
        showAlert('An unexpected error occurred. Please try refreshing the page.', 'error');
    });
}

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', function() {
    stopStatusPolling();
    uploadInProgress = false;
});

/**
 * Utility function to check if element exists
 */
function elementExists(id) {
    return document.getElementById(id) !== null;
}

/**
 * Utility function for safe DOM manipulation
 */
function safeUpdateElement(id, property, value) {
    const element = document.getElementById(id);
    if (element && property in element) {
        element[property] = value;
        return true;
    }
    return false;
}

/**
 * Export functions for use by other scripts
 */
window.AIUploader = {
    uploadFile: handleUpload,
    pollJobStatus: pollJobStatus,
    downloadResults: downloadResults,
    showAlert: showAlert,
    formatFileSize: formatFileSize,
    formatTime: formatTime,
    CONFIG: CONFIG
};

// Additional utility functions for status and history pages
if (typeof window !== 'undefined') {
    
    /**
     * Initialize status page specific functionality
     */
    window.initStatusPage = function() {
        // This would be called by status.html
        const urlParams = new URLSearchParams(window.location.search);
        const jobId = urlParams.get('job');
        
        if (jobId) {
            currentJobId = jobId;
            startStatusPolling(jobId);
        }
    };
    
    /**
     * Initialize history page specific functionality
     */
    window.initHistoryPage = function() {
        // This would be called by history.html
        // History page has its own embedded JavaScript
        console.log('History page initialized');
    };
}

// Console information for developers
console.log('AI Sales Agent Frontend v1.0.0 loaded');
console.log('Available global functions:', Object.keys(window.AIUploader || {}));