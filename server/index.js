const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const multer = require('multer');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 8080;

// Configure multer for file uploads
const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
        fileSize: 50 * 1024 * 1024, // 50MB limit
    },
    fileFilter: (req, file, cb) => {
        if (file.mimetype === 'application/pdf') {
            cb(null, true);
        } else {
            cb(new Error('Only PDF files are allowed'), false);
        }
    }
});

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Utility function to run Python script
function runPythonScript(scriptPath, args = []) {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [scriptPath, ...args]);
        
        let stdout = '';
        let stderr = '';
        
        pythonProcess.stdout.on('data', (data) => {
            stdout += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data) => {
            stderr += data.toString();
        });
        
        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                console.error(`Python process exited with code ${code}`);
                console.error('stderr:', stderr);
                reject(new Error(`Python script failed with code ${code}: ${stderr}`));
            } else {
                try {
                    // Try to parse JSON response
                    const result = JSON.parse(stdout.trim());
                    resolve(result);
                } catch (e) {
                    // If not JSON, return the raw output
                    resolve({ output: stdout.trim() });
                }
            }
        });
        
        pythonProcess.on('error', (error) => {
            console.error('Failed to start Python process:', error);
            reject(error);
        });
    });
}

// Utility function to call Python brain functions
async function callBrainFunction(functionName, data = {}) {
    const brainScriptPath = path.join(__dirname, '..', 'brainlib', 'brain.py');
    const args = [functionName, JSON.stringify(data)];
    
    try {
        const result = await runPythonScript(brainScriptPath, args);
        return result;
    } catch (error) {
        console.error(`Error calling brain function ${functionName}:`, error);
        throw error;
    }
}

// Utility function to call Python clustering functions
async function callClusterFunction(functionName, data = {}) {
    const clusterScriptPath = path.join(__dirname, '..', 'brainlib', 'cluster.py');
    const args = [functionName, JSON.stringify(data)];
    
    try {
        const result = await runPythonScript(clusterScriptPath, args);
        return result;
    } catch (error) {
        console.error(`Error calling cluster function ${functionName}:`, error);
        throw error;
    }
}

// Routes

// POST /note - Store a new note
app.post('/note', async (req, res) => {
    try {
        const { note } = req.body;
        
        if (!note || typeof note !== 'string' || note.trim() === '') {
            return res.status(400).json({
                success: false,
                error: 'Note is required and must be a non-empty string'
            });
        }
        
        console.log(`Storing note: "${note}"`);
        
        // Call Python brain function to store note
        const result = await callBrainFunction('store_note', { note: note.trim() });
        
        res.json({
            success: true,
            message: 'Note stored successfully',
            noteId: result.noteId || result.output,
            note: note.trim()
        });
        
    } catch (error) {
        console.error('Error storing note:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to store note',
            details: error.message
        });
    }
});

// POST /upload-pdf - Upload and store a PDF file
app.post('/upload-pdf', upload.single('pdf'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({
                success: false,
                error: 'PDF file is required'
            });
        }
        
        const { originalname, buffer } = req.file;
        
        console.log(`Processing PDF upload: ${originalname} (${buffer.length} bytes)`);
        
        // Convert buffer to base64 for Python processing
        const pdfBase64 = buffer.toString('base64');
        
        // Call Python brain function to store PDF
        const result = await callBrainFunction('store_pdf', { 
            pdf_base64: pdfBase64,
            filename: originalname
        });
        
        if (result.success) {
            res.json({
                success: true,
                message: 'PDF uploaded and processed successfully',
                pdfId: result.pdfId,
                filename: originalname,
                totalPages: result.total_pages,
                pagesWithText: result.pages_with_text,
                fileSizeBytes: result.file_size_bytes
            });
        } else {
            res.status(400).json({
                success: false,
                error: 'Failed to process PDF',
                details: result.error || 'Unknown error'
            });
        }
        
    } catch (error) {
        console.error('Error uploading PDF:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to upload PDF',
            details: error.message
        });
    }
});

// DELETE /note/:id - Delete a note
app.delete('/note/:id', async (req, res) => {
    try {
        const { id } = req.params;
        
        if (!id || typeof id !== 'string' || id.trim() === '') {
            return res.status(400).json({
                success: false,
                error: 'Note ID is required'
            });
        }
        
        console.log(`Deleting note with ID: ${id}`);
        
        // Call Python brain function to delete note
        const result = await callBrainFunction('delete_note', { note_id: id.trim() });
        
        if (result.deleted) {
            res.json({
                success: true,
                message: 'Note deleted successfully',
                noteId: id
            });
        } else {
            res.status(404).json({
                success: false,
                error: 'Note not found',
                noteId: id
            });
        }
        
    } catch (error) {
        console.error('Error deleting note:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to delete note',
            details: error.message
        });
    }
});

// GET /notes - Retrieve all notes
app.get('/notes', async (req, res) => {
    try {
        console.log('Retrieving all notes');
        
        // Call Python brain function to get all notes
        const result = await callBrainFunction('get_all_notes');
        
        res.json({
            success: true,
            notes: result.notes || result.output || [],
            count: (result.notes || result.output || []).length
        });
        
    } catch (error) {
        console.error('Error retrieving notes:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to retrieve notes',
            details: error.message
        });
    }
});

// GET /clusters - Get clustered notes
app.get('/clusters', async (req, res) => {
    try {
        const { k, auto_k = 'true', max_k = '10' } = req.query;
        
        // Parse parameters
        const autoK = auto_k.toLowerCase() === 'true';
        const maxK = parseInt(max_k);
        const numClusters = k ? parseInt(k) : null;
        
        // Validate parameters
        if (k && (isNaN(numClusters) || numClusters < 1)) {
            return res.status(400).json({
                success: false,
                error: 'Invalid number of clusters. Must be a positive integer.'
            });
        }
        
        if (isNaN(maxK) || maxK < 2) {
            return res.status(400).json({
                success: false,
                error: 'Invalid max_k. Must be at least 2.'
            });
        }
        
        console.log(`Retrieving clustered notes with auto_k=${autoK}, k=${numClusters}, max_k=${maxK}`);
        
        // Call Python clustering function to get clusters
        const result = await callClusterFunction('get_clusters', { 
            k: numClusters, 
            auto_k: autoK, 
            max_k: maxK 
        });
        
        if (result.success === false) {
            return res.status(500).json({
                success: false,
                error: 'Failed to generate clusters',
                details: result.error
            });
        }
        
        res.json({
            success: true,
            clusters: result.clusters || {},
            autoK: autoK,
            maxK: maxK,
            message: 'Clusters generated successfully'
        });
        
    } catch (error) {
        console.error('Error retrieving clusters:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to retrieve clusters',
            details: error.message
        });
    }
});

// GET /cluster-summary - Get cluster summary
app.get('/cluster-summary', async (req, res) => {
    try {
        const { auto_k = 'true', max_k = '10' } = req.query;
        
        // Parse parameters
        const autoK = auto_k.toLowerCase() === 'true';
        const maxK = parseInt(max_k);
        
        // Validate parameters
        if (isNaN(maxK) || maxK < 2) {
            return res.status(400).json({
                success: false,
                error: 'Invalid max_k. Must be at least 2.'
            });
        }
        
        console.log(`Retrieving cluster summary with auto_k=${autoK}, max_k=${maxK}`);
        
        // Call Python clustering function to get cluster summary
        const result = await callClusterFunction('get_cluster_summary', { 
            auto_k: autoK, 
            max_k: maxK 
        });
        
        if (result.success === false) {
            return res.status(500).json({
                success: false,
                error: 'Failed to generate cluster summary',
                details: result.error
            });
        }
        
        res.json({
            success: true,
            summary: result.summary || {},
            autoK: autoK,
            maxK: maxK,
            message: 'Cluster summary generated successfully'
        });
        
    } catch (error) {
        console.error('Error retrieving cluster summary:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to retrieve cluster summary',
            details: error.message
        });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        success: true,
        message: 'Digital Second Brain API is running',
        timestamp: new Date().toISOString()
    });
});

// Error handling middleware
app.use((error, req, res, next) => {
    if (error instanceof multer.MulterError) {
        if (error.code === 'LIMIT_FILE_SIZE') {
            return res.status(400).json({
                success: false,
                error: 'File too large. Maximum size is 50MB.'
            });
        }
    }
    
    if (error.message === 'Only PDF files are allowed') {
        return res.status(400).json({
            success: false,
            error: 'Only PDF files are allowed'
        });
    }
    
    console.error('Unhandled error:', error);
    res.status(500).json({
        success: false,
        error: 'Internal server error',
        details: error.message
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`Digital Second Brain API server running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
}); 