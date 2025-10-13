
steps for spech2 text 

<img width="1025" height="416" alt="image" src="https://github.com/user-attachments/assets/2b734a4c-a35f-4fa4-8c9a-434f0ed444ae" />

step 1. open anconda and type : conda activate signlang  

step 2. Install dependencies:
pip install vosk sounddevice  
If sounddevice gives errors  
conda install -c conda-forge portaudio  
step 3. Navigate to your project folder:cd path\to\SpeechToText  
step 4. run the script : python main.py
Speak into the microphone.
You should see real-time text printed in the terminal.
Press Ctrl+C to stop.
