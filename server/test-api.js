const axios = require('axios');

const API_BASE_URL = 'http://localhost:8080';

async function testAPI() {
    console.log('🧪 Testing Digital Second Brain API...\n');
    
    try {
        // Test health endpoint
        console.log('1. Testing health endpoint...');
        const healthResponse = await axios.get(`${API_BASE_URL}/health`);
        console.log('✅ Health check passed:', healthResponse.data.message);
        
        // Test storing a note
        console.log('\n2. Testing note storage...');
        const noteData = {
            note: "This is a test note from the API test script"
        };
        const storeResponse = await axios.post(`${API_BASE_URL}/note`, noteData);
        console.log('✅ Note stored successfully:', storeResponse.data.noteId);
        
        // Test retrieving all notes
        console.log('\n3. Testing note retrieval...');
        const notesResponse = await axios.get(`${API_BASE_URL}/notes`);
        console.log('✅ Notes retrieved successfully. Count:', notesResponse.data.count);
        console.log('Notes:', notesResponse.data.notes);
        
        // Test clusters endpoint
        console.log('\n4. Testing clusters endpoint...');
        const clustersResponse = await axios.get(`${API_BASE_URL}/clusters`);
        console.log('✅ Clusters retrieved successfully:', clustersResponse.data.clusters);
        
        console.log('\n🎉 All API tests passed!');
        
    } catch (error) {
        console.error('❌ API test failed:', error.response?.data || error.message);
    }
}

// Run tests if this script is executed directly
if (require.main === module) {
    testAPI();
}

module.exports = { testAPI }; 