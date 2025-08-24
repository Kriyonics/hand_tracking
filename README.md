# hand_tracking
# Steps for activating anconda
In that Anaconda Prompt, type:
conda create -n signlang python=3.10
# Step 2: Activate Environment
Once installed, activate it:
conda activate signlang
Now you should see:
(signlang) C:\Users\YourName>
then to Open Jupyter from (signlang) environment type:
jupyter notebook
# Step 3: Install Packages
Now install MediaPipe and other dependencies:
pip install mediapipe opencv-python tensorflow notebook matplotlib scikit-learn

# Test MediaPipe in Notebook
Inside a new cell, try:
import mediapipe as mp
print("MediaPipe version:", mp.__version__)
If it prints the version (like 0.10.x)
