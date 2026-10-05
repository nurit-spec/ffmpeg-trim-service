import os
import subprocess
import tempfile
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

@app.route('/trim', methods=['POST'])
def trim_video():
    try:
        data = request.json
        video_url = data.get('video_url')
        trims = data.get('trims', [])

        if not video_url or not trims:
            return jsonify({'error': 'Missing video_url or trims'}), 400

        input_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        output_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name

        # Download raw video
        subprocess.run(['curl', '-L', '-o', input_file, video_url], check=True)

        # Build FFmpeg trim & concat filter string
        filter_str = ""
        concat_str = ""
        for i, trim in enumerate(trims):
            start = trim['start']
            end = trim['end']
            filter_str += f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];"
            filter_str += f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];"
            concat_str += f"[v{i}][a{i}]"

        filter_str += f"{concat_str}concat=n={len(trims)}:v=1:a=1[outv][outa]"

        # Run FFmpeg command
        cmd = [
            'ffmpeg', '-y', '-i', input_file,
            '-filter_complex', filter_str,
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac',
            output_file
        ]
        subprocess.run(cmd, check=True)

        # Send back trimmed video
        return send_file(output_file, mimetype='video/mp4', as_attachment=True, download_name='edited_video.mp4')

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
