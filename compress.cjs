const ffmpeg = require('@ffmpeg-installer/ffmpeg');
const { execSync } = require('child_process');
execSync(`"${ffmpeg.path}" -y -i ../webhook-server-cuong/assets/cinematic-bgm.mp3 -b:a 48k -ac 1 compressed-bgm.mp3`);
