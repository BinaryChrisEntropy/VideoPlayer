
import tkinter as tk
from tkinter import filedialog
import ffmpeg
import numpy as np
from PIL import Image, ImageTk
import time
import pyaudio
from threading import Thread

class Media:
    def __init__(self):
        self.process_audio = None
        self.process_video= None
        self.resolution = None
        self.path = None
        self.audio_stream_out = None
        self.process_audio_out = pyaudio.PyAudio()
        self.pts = []
        self.w = None
        self.h = None

    
    
    def load_media(self, path):
        probe = ffmpeg.probe(path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        self.path = path
        self.w = int(video_stream['width'])
        self.h = int(video_stream['height'])
        self.resolution = (self.w, self.h)
        
        self.process_video = (ffmpeg.input(self.path)
                         .output('pipe:', format='rawvideo', pix_fmt='rgb24')
                         .run_async(pipe_stdout=True, quiet=True))
        
        self.process_audio = (ffmpeg.input(self.path)
                         .output('pipe:', format='f32le')
                         .run_async(pipe_stdout=True, quiet=True))
        
        self.audio_stream_out = self.process_audio_out.open(format=pyaudio.paFloat32, channels=1, rate=96000, output=True)
        
         
        self.pts.clear()
        
        while True:
            video_bytes = self.process_video.stdout.read(self.w*self.h*3)
            # fps ... 30
            # sr  ... 96000
            # channel ... 1
            # 96000 / 30 * 64 / 8 * 1
            audio_bytes = self.process_audio.stdout.read(12800)       
            self.pts.append((video_bytes, audio_bytes))  
            
            if not video_bytes and not audio_bytes:
                print("Media fully loaded!")
                break
            
            
    def get_media(self, index=0):
        for pts in self.pts[index:]:
            yield pts
    
    
    def __str__(self):
        return self.path
    
class Player:
    def __init__(self) -> None:
        #self.views = []
        self.view = None
        self.media = None
        self.index = 0
        self.PLAY = False
        self.PAUSE = False
        self.stream = None
        self.vol = 5.
             
    def set_view(self, view):
        self.view = view
            
    def set_media(self, media):    
        self.media = media
            
    def play(self, index=0):
        if not self.PLAY:
            self.PLAY = True
            self.PAUSE = False
            self.index = index
        
            for i, frame in enumerate(self.media.get_media(self.index)):
                # to do convert to numpy array similar to video and change volumne
                try:
                    audio_ = np.frombuffer(frame[1], dtype=np.float32) * (self.vol * 0.1)
                    print(audio_)
                    audio = audio_.tobytes()
                except:
                    pass
                
                if not self.PLAY:
                    break
                if self.PAUSE:
                    self.index += i
                    self.PLAY = False
                    self.PAUSE = False
                    return
                try:
                    video = np.frombuffer(frame[0], np.uint8).reshape([self.media.w, self.media.h, 3])
                    img = ImageTk.PhotoImage(Image.fromarray(video))
                    
                    canvas = self.view.children["!canvas"]
                    canvas.create_image(video.shape[0]/4, video.shape[1]/4, image=img)
                    self.view.update()
                except:
                    pass
                
                self.media.audio_stream_out.write(audio)
            
            self.PLAY = False
            self.PAUSE = False
            self.index = 0
            

    def stop(self):
        self.PLAY = False
        self.index = 0

    def pause(self):
        self.PAUSE = True
            
    def resume(self, index):
        if index > 0:
            self.play(index)

    def set_volume(self, vol):
        self.vol = vol


        
class Gui():
    def __init__(self):
        self.file_name = None
        self.win = tk.Tk()
        self.win.geometry("1080x728")
        self.win.title("VP")
        
        self.menu = tk.Menu(self.win)
        self.f_menu = tk.Menu(self.menu)
        self.f_menu.add_command(label="Open", command=self.open_media)
        self.menu.add_cascade(label="File", menu=self.f_menu)
        
        
        self.media_title = tk.Label(self.win, text="Media titel")
        self.media_title.pack(fill=tk.BOTH)
        
        self.canvas = tk.Canvas(width=600, height=400)
        self.canvas.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        
        
        self.manager = {}
        self.items = []
        self.var = tk.StringVar()
        self.list = tk.Listbox(self.win, listvariable=self.var)
        self.list.pack(side=tk.RIGHT)
        

        #self.media = Media()
        self.player = Player()
        self.player.set_view(self.win)
        
        self.btns = tk.Frame(master=self.win)
        self.btns.pack(anchor=tk.S, fill=tk.BOTH, side=tk.BOTTOM)
        self.btn_play = tk.Button(self.btns, text="Play", command=self.play_media)
        self.btn_stop = tk.Button(self.btns, text="Stop", command=self.stop_media)
        self.btn_pause = tk.Button(self.btns, text="Pause", command=self.pause_media)
        self.btn_resume = tk.Button(self.btns, text="Resume", command=self.resume_media)
        self.btn_play.pack(side=tk.LEFT)
        self.btn_stop.pack(side=tk.LEFT)
        self.btn_pause.pack(side=tk.LEFT)
        self.btn_resume.pack(side=tk.LEFT)
        
    
        self.scaler_vol = tk.Scale(self.btns, from_=0, to=10, orient="horizontal", resolution=0.1, tickinterval=10,
                                   length=200, showvalue=0, label="Volume",
                                   command=lambda x : self.player.set_volume(((float(x)))))
        
        self.scaler_vol.set(5.)
        
        self.scaler_vol.pack(side=tk.LEFT, padx=(10, 0), pady=(10, 10))
        self.win.config(menu=self.menu)
         
        self.win.mainloop()
       
    def open_media(self):
        #self.file_name = filedialog.askopenfilename()
        #self.media_title["text"] = self.file_name
        #self.media.load_media(self.file_name)
        self.file_names = filedialog.askopenfilenames()

        for name in self.file_names:
            if not name in self.items: 
                self.items.append(name)
        self.var.set(self.items)
        
        for key in self.items:
            if not key in self.manager.keys():
                media = Media()
                t = Thread(target=media.load_media, args=(key,))
                t.start()
                self.manager[key] = media

            #media.load_media(key)
            
            
    def play_media(self):
        key = self.list.get(self.list.curselection())
        self.player.set_media(self.manager[key])
        self.player.play()      
           
    def pause_media(self):
        self.player.pause()
     
    def stop_media(self):
        self.player.stop()
        
    def resume_media(self):
        self.player.resume(self.player.index)
      
if __name__ == "__main__":
    gui = Gui()
    
