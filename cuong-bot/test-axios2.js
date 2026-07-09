import axios from 'axios';
async function run() {
  try {
    const res = await axios.get(`https://api.pexels.com/videos/search`, {
      params: { query: '', orientation: 'portrait', per_page: 1 },
      headers: { Authorization: undefined }
    });
    console.log("SUCCESS:", res.status);
  } catch(e) {
    console.log("ERROR:", e.response ? e.response.status : e.message);
    if(e.response && e.response.data) console.log("DATA:", e.response.data);
  }
}
run();
