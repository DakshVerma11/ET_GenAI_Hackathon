document.addEventListener('DOMContentLoaded', () => {
    let globalData = {
        dashboard: null,
        scriptJson: null
    };

    const btn1 = document.getElementById('btnStep1');
    const btn2 = document.getElementById('btnStep2');
    const btn3 = document.getElementById('btnStep3');

    const status1 = document.getElementById('status1');
    const status2 = document.getElementById('status2');
    const status3 = document.getElementById('status3');

    const card1 = document.getElementById('cardStep1');
    const card2 = document.getElementById('cardStep2');
    const card3 = document.getElementById('cardStep3');

    const idleState = document.getElementById('idleState');
    const jsonViewer = document.getElementById('jsonViewer');
    const videoContainer = document.getElementById('videoContainer');
    const videoPlayer = document.getElementById('videoPlayer');
    const viewerType = document.getElementById('viewerType');

    function showJson(data, title) {
        idleState.style.display = 'none';
        videoContainer.style.display = 'none';
        jsonViewer.style.display = 'block';
        jsonViewer.textContent = JSON.stringify(data, null, 2);
        viewerType.textContent = title;
    }

    function showVideo(url) {
        idleState.style.display = 'none';
        jsonViewer.style.display = 'none';
        videoContainer.style.display = 'flex';
        videoPlayer.src = url;
        videoPlayer.play();
        viewerType.textContent = 'Rendered Video';
    }

    btn1.addEventListener('click', async () => {
        btn1.innerHTML = '<span class="loader"></span> Fetching...';
        btn1.disabled = true;
        status1.textContent = 'Extracting market data...';
        
        try {
            const res = await fetch('/api/video/fetch');
            const data = await res.json();
            
            globalData.dashboard = data.dashboard;
            
            btn1.innerHTML = 'Data Fetched ✓';
            status1.textContent = 'Data extracted successfully.';
            card1.classList.remove('active');
            card1.classList.add('done');
            
            // Enable next step
            card2.classList.add('active');
            btn2.disabled = false;
            status2.textContent = 'Ready to generate AI script';
            
            showJson(data.dashboard, 'Market Data JSON');

            btn1.disabled = false;
        } catch (e) {
            btn1.innerHTML = 'Fetch Failed';
            status1.textContent = e.message;
            btn1.disabled = false;
        }
    });

    btn2.addEventListener('click', async () => {
        btn2.innerHTML = '<span class="loader"></span> Writing Script...';
        btn2.disabled = true;
        status2.textContent = 'Generating scene structures...';
        
        try {
            const res = await fetch('/api/video/generate_script', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ dashboard: globalData.dashboard })
            });
            const data = await res.json();
            
            if(data.status !== 'success') throw new Error(data.message || 'Generation failed');
            
            globalData.scriptJson = data.script_json;
            
            btn2.innerHTML = 'Script Ready ✓';
            status2.textContent = 'Script generated successfully.';
            card2.classList.remove('active');
            card2.classList.add('done');
            
            // Enable next
            card3.classList.add('active');
            btn3.disabled = false;
            status3.textContent = 'Ready to render';
            
            showJson({ script: data.script_json, prompt: data.prompt }, 'Engine Script JSON');

            btn2.disabled = false;
        } catch (e) {
            btn2.innerHTML = 'Generation Failed';
            status2.textContent = e.message;
            btn2.disabled = false;
        }
    });

    btn3.addEventListener('click', async () => {
        btn3.innerHTML = '<span class="loader"></span> Rendering...';
        btn3.disabled = true;
        status3.textContent = 'Synthesizing voice & rendering visuals (takes 1-2 mins)...';
        
        try {
            const res = await fetch('/api/video/generate_video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    dashboard: globalData.dashboard,
                    script_json: globalData.scriptJson
                })
            });
            const data = await res.json();
            
            if(data.status !== 'success') throw new Error(data.error || 'Render failed');
            
            btn3.innerHTML = 'Render Complete ✓';
            status3.textContent = 'Video saved locally.';
            card3.classList.remove('active');
            card3.classList.add('done');
            
            // The video_path that's returned is likely an absolute path or relative to project root.
            // But main.py now serves the root as /static or we can add a specific route to serve the video.
            // Let's assume there's an /outputs route or it's within root.
            showVideo('/video_output/' + data.video_path.split(/[\\/]/).pop());
            // We might need to map /video_output in main.py to fetch the actual video!

        } catch (e) {
            btn3.innerHTML = 'Render Failed';
            status3.textContent = e.message;
            btn3.disabled = false;
        }
    });
});
