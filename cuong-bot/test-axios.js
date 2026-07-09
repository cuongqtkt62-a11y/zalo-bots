import axios from 'axios';
async function run() {
  try {
    const query = "câu nói hay về thành công, cinematic, 4k";
    const res = await axios.get(`https://api.pexels.com/videos/search`, {
      params: { query, orientation: 'portrait', per_page: 1 },
      headers: { Authorization: "SOME_KEY" }
    });
    console.log("SUCCESS:", res.status);
  } catch(e) {
    console.log("ERROR:", e.response ? e.response.status : e.message);
    if(e.response && e.response.data) console.log("DATA:", e.response.data);
  }
}
run();
