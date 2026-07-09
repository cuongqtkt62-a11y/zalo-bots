import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';

const supabaseUrl = "https://cdupwjjmkvvulztudtvi.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkdXB3ampta3Z2dWx6dHVkdHZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIzOTIxMjgsImV4cCI6MjA5Nzk2ODEyOH0.xtc_no_0C4efkm6py0Lq3kJYZCwqMVnMBkFuRthUBRo";
const supabase = createClient(supabaseUrl, supabaseKey);

async function upload() {
  const content = readFileSync('./cuong-bot/zalo-credentials-cuong.json');
  const { data, error } = await supabase.storage.from('zalo-bot-state').upload('cuong/zalo-credentials-cuong.json', content, { upsert: true });
  if (error) console.error(error);
  else console.log('Successfully uploaded cuong credentials to Supabase!');
}
upload();
