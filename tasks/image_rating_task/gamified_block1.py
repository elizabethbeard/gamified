# written by liz beard
# last updated 20240611

from psychopy import visual, core, event, data, logging
import pandas as pd
import numpy as np
import os
import socket
import time
import re

# Debug/Testing, set to False for data collection
Debug = False

# C:\Users\bhlabras\Desktop\Beard\gamified_block1.py
base_dir = os.path.abspath(r"C:\Users\bhlabras\Desktop\Beard") #pc
#base_dir = os.path.getcwd() #mac

# clear any existing event parameters
event.globalKeys.clear()

# function to save any existing data if we quit mid-block. may still throw some errors if it's trying to write to outfile.
def saveout():
    
    quit_message = f'************ Block 1 QUIT, unix: {time.time()}, core: {core.getTime()} ************'
    
    if trials is not None and data_file is not None:
        print("trial data saved")
        trials.saveAsWideText(data_file, delim=',', appendFile=True)
        
    if log_file is not None:
        print("log_file saved")
        logging.exp(quit_message)
        logging.flush()
        
    if output_file is not None:
        print("output_file saved")
        output_file.write(quit_message)
        output_file.close()
        
    core.quit()

event.globalKeys.add(key='x', func=saveout) #press x to quit experiment and save any data mid-run

# participant id function
def check_participant_id(participant_id):
    # Define the regex pattern for 'sub-###'
    pattern = re.compile(r'^sub-\d{3}$')
    
    # Check if the participant ID matches the pattern
    if pattern.match(participant_id):
        return True
    else:
        return False

# iMotions connection setup
UDP_IP="127.0.0.1"
UDP_PORT=8089 

def sendudp(string_for_iMotions, output_file=None):
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.sendto(bytes(string_for_iMotions,"utf-8"),(UDP_IP,UDP_PORT))
    sock.close()
    print('message sent: ',string_for_iMotions)
    
    if output_file is not None:
        output_file.write('message sent: '+string_for_iMotions)

def iMT_RemoteControlAPI(TCP, command, field=None, output_file=None):
    """
    This function sends a command to iMotions' using the TCP port and waits
    for a complete response (\r\n)

    :param TCP: TCP client (socket object)
    :param command: Command to send to iMotions
    :param field: Specified 'field' to return (optional)
    :return: Returns the part of iMotions response before '\r\n' (or only a specified field)
    """
    # Transform the command string (UTF8 encoding)
    C_UTF8 = command.encode('utf-8')

    # Send command and wait for a complete response (\r\n)
    R_UTF8 = b''
    complete = False

    message_delimiter = b'\r\n'

    # Send the command
    TCP.sendall(C_UTF8)

    # Wait until complete
    while not complete:
        # Read the response
        data = TCP.recv(1024)  # Buffer size is 1024 bytes
        R_UTF8 += data

        # Evaluate
        if message_delimiter in R_UTF8:
            complete = True

    # Transform the response (UTF8 encoding)
    R_Transform = R_UTF8.decode('utf-8')
    print(f'\n Response: {R_Transform} \n')
    
    if output_file is not None:
        output_file.write("Response:" + R_Transform)

    # Return iMotions' full response or only a specified field
    if field is None:
        return R_Transform
    else:
        split_response = R_Transform.split(';')
        return split_response[field]

    print('\n iMT_RemoteControlAPI DONE. \n')
    if output_file is not None:
        output_file.write('iMT_RemoteControlAPI DONE. \n')

# Remote Control
TCP_PORT_REMOTE=8087 #iMotions Remote Control Port

# get subj ID from iMotions
if Debug == True:
    subj_id = 'sub-999'
    output_file_path = os.path.join(base_dir, 'logs', subj_id, f'{subj_id}_block-1_APIoutput-file.txt')
    output_file = open(output_file_path, 'w')
    output_file_created = f'Subject ID -- DEBUG: {subj_id}\n'
    output_file.write(output_file_created)

else:
    try:
        TCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        TCP.connect((UDP_IP, TCP_PORT_REMOTE))
        
        response = iMT_RemoteControlAPI(TCP, 'R;2;;STATUS\r\n', 9)
        
        if response is not None:
            print(f'Received Response: {response}')
            subj_id = response
            
            subj_check = check_participant_id(subj_id)
            
            if subj_check == False:
                print('Did you enter the subject ID correctly? sub-###')
                print('Press any key to exit.')
                event.waitKeys()
                core.quit()
            else:
            # setup output file
                output_file_path = os.path.join(base_dir, 'logs', subj_id, f'{subj_id}_block-1_APIoutput-file.txt')
                output_file = open(output_file_path, 'w')
                output_file.write("Received Respones: " + response)
    
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")
        
    finally:
        TCP.close()

# iMotions message defaults
event_message_for_iMotions="M;1;;;{};{}\r\n" # "M;1;;;{EventLabel};{EventText}\r\n"
scene_message_for_iMotions="M;2;;;{};{};{};{}\r\n" # "M;2;;;{EventLabel};{EventText};{MarkerType};{SceneType}\r\n"

# Load the CSV file
file_path = os.path.join(base_dir,'logs',subj_id,'image_lists',f'randomized_{subj_id}_part1.csv')  # Update with the correct path
if os.path.exists(file_path) == False:
    print('Cannot find ',file_path)
    print('Press any key to exit')
    event.waitKeys()
    core.quit()
image_list = pd.read_csv(file_path)

# Extract image filenames & condition
trials_data = [{'image_file': row['Image'], 'category': row['Category']} for index, row in image_list.iterrows()]
image_files = image_list['Image'].tolist()
categories = image_list['Category'].to_list()

# Initialize the window
if Debug == True:
    win = visual.Window(monitor='Dell', size=(1290,1080), units='pix', screen=1)
    #win = visual.Window(size=(800, 600), units='pix')
else:
    win = visual.Window(monitor='Dell', size=(1290,1080), units='pix', screen=1)

# Initialize fixation cross
fixation = visual.TextStim(win, text='+', height=75, color="yellow")

# intialize rating scales
rating_max = 30 #15s max for ratings, right now

# Get window dimensions
x, y = win.size  # for converting norm units to pix

# Define the spacing between scales
spacing = y / 5.5  # Even spacing between the scales
start_y = y / 3  # Starting y position for the top scale

# Calculate the positions for the four scales
vertical_positions = [start_y - i * spacing for i in range(5)]

myRatingScale1 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,100],
                                    labels=['\nnot strongly\nemotional','\nstrongly\nemotional'],
                                    scale='How emotionally intense is this image?',
                                    showAccept=False, mouseOnly=True, size=0.7, pos=(0, vertical_positions[0]),
                                    stretch=2.5, markerStart=50)
myRatingScale2 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,50,100],
                                    labels=['\nvery\nnegative','\nneutral','\nvery\npositive'],
                                    scale='How positive or negative is this image?',
                                    showAccept=False, mouseOnly=True, size=0.7, pos=(0, vertical_positions[1]),
                                    stretch=2.5, markerStart=50)
myRatingScale3 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,100],
                                    labels=['\nvery \nnegative','\nvery\npositive'],
                                    scale='How does this image make you feel?',
                                    showAccept=False, mouseOnly=True, size=0.7, pos=(0, vertical_positions[2]),
                                    stretch=2.5, markerStart=50)                                    
myRatingScale4 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,50,100],
                                    labels=['\nnot at all\nexciting','\nmoderately\nexciting','\nvery\nexciting'],
                                    scale='How exciting is this image?',
                                    showAccept=False, mouseOnly=True, size=0.7, pos=(0, vertical_positions[3]),
                                    stretch=2.5, markerStart=50)
submitRatings = visual.TextStim(win, text="Press [Enter] to submit each rating.", height=30, units='pix', 
                        anchorHoriz='center', anchorVert='center',
                        color='LightGray', pos=(0, vertical_positions[3]-150), wrapWidth=4000)
                        

ratings_dict = {"intensity" : myRatingScale1,
                "valence" : myRatingScale2,
                "personal" : myRatingScale3,
                "arousal" : myRatingScale4}

# Function to generate fixation times following an exponential distribution
# not using anymore
def generate_fixation_time():
    return np.random.exponential(scale=1.5) + 3

# Function to generate display times following a normal distribution
def generate_display_time(amount):
    return np.random.normal(loc=amount, scale=0.25)

# Function to generate random position within window bounds
def random_position():
    x = np.random.uniform(-win.size[0]//2 + 50, win.size[0]//2 - 50)
    y = np.random.uniform(-win.size[1]//2 + 50, win.size[1]//2 - 50)
    return (x, y)

# Set up trial handler
trials = data.TrialHandler(
    trials_data,
    nReps=1, method='sequential'
)

# timerrr
timer = core.Clock()

# Set up logging
logging.setDefaultClock(core.Clock()) # we may want to change this later
log_file = os.path.join(base_dir, 'logs', subj_id, f'{subj_id}_block-1_experiment-log.csv')
data_file = os.path.join(base_dir, 'logs', subj_id, f'{subj_id}_block-1.csv')
logging.LogFile(log_file, level=logging.INFO, filemode='w')

# get a "frame rate thing" out of the way
spaceToStart = visual.TextStim(win, text='Press [i] to continue. Remember to keep your head still.', color='white', height=35)#, height=100)
spaceToStart.draw()
win.flip()
event.waitKeys(keyList=('i'))

# Start the experiment
start_message = f'************ Begin Block 1, unix: {time.time()}, core: {core.getTime()} ************'
output_file.write(start_message+"\n")
logging.exp(start_message)
logging.flush()

# main task:
for trial in trials:
    
    event.Mouse(visible=False)

    # i'm not gonna look at the unpleasant ones if I don't have to tbh
    if Debug == True:
        if trial['category'] == "Unpleasant":
            continue
    
    # start iMotions scene recording
    try:
        sendudp(scene_message_for_iMotions.format(trial['image_file'],trial['category'],'N','V'), output_file)
        
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")
    
    # Show fixation cross
    fixation.pos = random_position()
    if Debug == True:
        fixation_time = .5 
    else:
        fixation_time = generate_display_time(amount=3)
        fixation_time = np.clip(fixation_time, 2.75, 6)  # Ensure display time is between 2.75 and 6 seconds
    trials.addData("fixationtTime", fixation_time)
    fixation_onset = core.getTime()
    fixation_onset_unix = time.time()
    try: # and some point this should end up in the sendudp/sendtdp function itself
        sendudp(event_message_for_iMotions.format('fixationEvent','onset'), output_file)
        
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")
    trials.addData("fixationOnset_unix", fixation_onset_unix)
    fixation.draw()
    win.flip()
    core.wait(fixation_time) # i think core.wait should be fine for now
    try:
        sendudp(event_message_for_iMotions.format('fixationEvent','offset'), output_file)
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")
    fixation_offset = core.getTime()
    fixation_offset_unix = time.time()
    trials.addData("fixationOffset_unix", fixation_offset_unix)
    
    event.Mouse(visible=False)

    # Show image
    if Debug == True:
        display_time = 3
    else:
        display_time = generate_display_time(amount=5)
        display_time = np.clip(display_time, 5, 6)  # Ensure display time is between 5 and 6 seconds
    trials.addData("displayTime", display_time)
    image_path = os.path.join(base_dir, 'study1-images_v1-20240602', trial['image_file'])
    image_onset = core.getTime()
    image_onest_unix = time.time()
    trials.addData("imageOnset_unix", image_onest_unix)
    try:
        sendudp(event_message_for_iMotions.format(trial['image_file'],'onset'), output_file)
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")
    image = visual.ImageStim(win, image=image_path)#, size=(400, 300))
    image.draw()
    win.flip()
    core.wait(display_time)
    try:
        sendudp(event_message_for_iMotions.format(trial['image_file'],'offset'), output_file)
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")
    image_offset = core.getTime()
    image_offset_unix = time.time()
    trials.addData("imageOffset_unix", image_offset_unix)
    
    # Collect Ratings
    ratings_onset = core.getTime()
    ratings_onset_unix = time.time()
    trials.addData('ratingOnset_unix', ratings_onset_unix)
    try:
        sendudp(event_message_for_iMotions.format('ratingEvent','onset'), output_file)
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")
    
    timer.reset()
    event.clearEvents()
    event.Mouse(visible=True)
    
    while (myRatingScale1.noResponse or myRatingScale2.noResponse or myRatingScale3.noResponse or myRatingScale4.noResponse) and timer.getTime() < rating_max:
        submitRatings.draw()
        myRatingScale1.draw()
        myRatingScale2.draw()
        myRatingScale3.draw()
        myRatingScale4.draw()
        win.flip()
    
    ratings_offset = core.getTime()
    ratings_offset_unix = time.time()
    rating_display_time = ratings_offset-ratings_onset
    trials.addData('ratingOffset_unix', ratings_offset_unix)
    try:
        sendudp(event_message_for_iMotions.format('ratingEvent','offset'), output_file)
    except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
    except Exception as e:
        exception_error_message = f"An unexpected error occured: {e}"
        print(exception_error_message)
        output_file.write(exception_error_message+"\n")

    for label, ratings in ratings_dict.items():
        
        if ratings.noResponse:
            
            scale_history = ratings.getHistory()
            scale_history_recent = scale_history[-1]
            scale_history_score, scale_history_rt = scale_history_recent
            
            scale_noResponse = f'Rating, {label}, not submitted, {scale_history}'
            logging.data(scale_noResponse)
            output_file.write(scale_noResponse+'\n')
            trials.addData(f'{label}Rating', 'not submitted')
            trials.addData(f'{label}Score', scale_history_score)
            trials.addData(f'{label}RT', scale_history_rt)
            
        else:
            scale_response = f'Rating, {label}, submitted, {ratings.getRating()}, {ratings.getRT()}'
            logging.data(ratings.getRating())
            output_file.write(scale_response+'\n')
            trials.addData(f'{label}Rating', 'submitted')
            trials.addData(f'{label}Score', ratings.getRating())
            trials.addData(f'{label}RT', ratings.getRT())
        
        ratings.reset()

    # Log events
    trials.addData('ratingDisplayTime', rating_display_time)
    logging.data(f'Fixation, onset: {fixation_onset:.4f}, offset: {fixation_offset:.4f}, duration: {fixation_time:.4f}')
    logging.data(f'Image, onset: {image_onset:.4f}, offset: {image_offset:.4f}, duration: {display_time:.4f}')
    logging.data(f'Rating, onset: {ratings_onset:.4f}, offset: {ratings_offset:.4f}, duration: {rating_display_time:.4f}')
    logging.flush()

# Close the window
win.close()
trials.saveAsWideText(data_file, delim=',', appendFile=True)
end_message = f'************ End Block 1, unix: {time.time()}, core: {core.getTime()} ************'
output_file.write(end_message+"\n")
logging.exp(end_message)
logging.flush()

try:
    TCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    TCP.connect((UDP_IP, TCP_PORT_REMOTE))

    response = iMT_RemoteControlAPI(TCP, 'R;1;;SLIDESHOWNEXT\r\n', 6, output_file)
    
    if response is not None:
        print(f'Received Response: {response}')
        output_file.write('Received Response: '+response+'\n')

except socket.error as e:
        socket_error_message = f"Socket error: {e}"
        print(socket_error_message)
        output_file.write(socket_error_message+"\n")
        
except Exception as e:
    exception_error_message = f"An unexpected error occured: {e}"
    print(exception_error_message)
    output_file.write(exception_error_message+"\n")
    
finally:
    TCP.close()

output_file.close()
core.quit()
