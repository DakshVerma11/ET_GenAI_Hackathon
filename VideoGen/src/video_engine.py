from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import os

def create_macro_video(audio_paths: list, scene_paths: list, caption_paths: list, output_path: str):
    """Stitches multi-scenes pairing exact isolated audio files and dynamic graphic captions perfectly."""
    clips = []
    
    # We must strictly map each scene directly to its explicit voiceover mp3
    for idx, (img_path, aud_path, cap_path) in enumerate(zip(scene_paths, audio_paths, caption_paths)):
        aud_clip = AudioFileClip(aud_path)
        
        # Pad duration slightly so audio doesn't clip off abruptly
        dur = aud_clip.duration + 0.3
        
        # Initialize explicit 24fps frame bounds to eliminate visual tearing
        img_clip = ImageClip(img_path).set_duration(dur).set_fps(24).set_audio(aud_clip)
        
        # Dynamic Shorts Caption overlay with pop-in animation (fade in fast)
        cap_clip = ImageClip(cap_path).set_duration(dur).set_fps(24).crossfadein(0.3)
        
        # Composite together
        clip = CompositeVideoClip([img_clip, cap_clip]).set_duration(dur)
        
        # Add smooth cinematic composited Crossfades
        if idx > 0:
            clip = clip.crossfadein(0.5)
            
        clips.append(clip)
        
    # method="compose" calculates alpha blending for crossfades with embedded audio tracks perfectly
    video = concatenate_videoclips(clips, method="compose")
    
    video.write_videofile(
        output_path, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac",
        threads=4,
        preset="ultrafast"
    )
    
    return output_path
