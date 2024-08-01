 # written by liz beard
# updated 20240618-1142AM
# to do:
#   - add iMotions event logging (if we want it)
#   - add psychopy logging (we need it)
#   - add output_file stuff (yeah)
#   - add something to double check the formatting of the subject id

from psychopy import visual, core, event, data, logging
import pandas as pd
import numpy as np
import hashlib
import random
import os
import socket
import time
import re

# C:\Users\bhlabras\Desktop\Beard\gamified_taskInstructions.py
base_dir = os.path.abspath(r"C:\Users\bhlabras\Desktop\Beard") # for pc
#base_dir = os.getcwd() # for mac

# Debug/Testing, set to False for data collection
Debug = False

# function to save any existing data if we quit mid-block. may still throw some errors if it's trying to write to outfile.
def saveout():
    
    quit_message = f'************ Task Instructions QUIT, unix: {time.time()}, core: {core.getTime()} ************'
        
    if output_file is not None:
        print("output_file saved")
        output_file.write(quit_message)
        output_file.close()
        
    core.quit()

# participant id function
def check_participant_id(participant_id):
    # Define the regex pattern for 'sub-###'
    pattern = re.compile(r'^sub-\d{3}$')
    
    # Check if the participant ID matches the pattern
    if pattern.match(participant_id):
        return True
    else:
        return False

event.globalKeys.add(key='x', func=saveout) #press x to quit experiment and save any data mid-run

# iMotions connection functions - just TDP for remote control
UDP_IP="127.0.0.1"
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

# initialize instruction text
# Initialize the window
if Debug == True:
    #win = visual.Window(monitor='Dell', size=(1290,1080), units='pix', screen=1)
    win = visual.Window(size=(1290, 1080), units='pix')
else:
    win = visual.Window(monitor='Dell', size=(1290,1080), units='pix', screen=1)

# set up subject stuff and randomization
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
                os.makedirs(os.path.join(base_dir, 'logs', subj_id), exist_ok=True)
                output_file_path = os.path.join(base_dir, 'logs', subj_id, f'{subj_id}_instructions_APIoutput-file.txt')
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

def extract_image_number(image_name):
    """
    Extract the image number from the filename. Handles cases with and without the "Game#" prefix.
    """
    basename = os.path.basename(image_name)
    if "Game" in basename:
        # Remove "Game#" prefix if it exists
        basename = "_".join(basename.split('_')[1:])
    # Extract the image number (assumes it is the part after the underscore and before the extension)
    image_number = os.path.splitext(basename)[0]
    return image_number

def randomize_images(df, subject_id):
    # Convert subject ID to a seed for reproducibility
    seed = int(hashlib.md5(subject_id.encode()).hexdigest(), 16) % (2**32)
    np.random.seed(seed)

    # Extract relevant columns and corresponding categories
    images = df[['IAPS Source file', 'Game6 - Black and White', 'Game2 - Cartoon style#1']].values
    categories = df['Category'].values
    sources = ['IAPS', 'Game6', 'Game2']
    
    # Flatten the list of images and pair with categories and sources
    image_list = []
    for i in range(images.shape[0]):
        for j in range(images.shape[1]):
            image_list.append((images[i, j], categories[i], sources[j]))

    # Randomize the order of the image list
    np.random.shuffle(image_list)

    # Ensure no two images from the same row are in the same split
    def ensure_unique_rows(image_list):
        split_1, split_2, split_3 = [], [], []
        row_ids_split_1, row_ids_split_2, row_ids_split_3 = set(), set(), set()
        
        for image in image_list:
            try:
                # Extract row_id in a more robust way
                row_id = extract_image_number(image[0])
            except IndexError:
                print(f"Warning: Skipping image with unexpected format: {image[0]}")
                continue

            if row_id not in row_ids_split_1:
                split_1.append(image)
                row_ids_split_1.add(row_id)
            elif row_id not in row_ids_split_2:
                split_2.append(image)
                row_ids_split_2.add(row_id)
            else:
                split_3.append(image)
                row_ids_split_3.add(row_id)
        
        # Balance the splits if needed
        while len(split_1) < 30:
            if split_2:
                split_1.append(split_2.pop(0))
            elif split_3:
                split_1.append(split_3.pop(0))
        while len(split_2) < 30:
            if split_1:
                split_2.append(split_1.pop(0))
            elif split_3:
                split_2.append(split_3.pop(0))
        while len(split_3) < 30:
            if split_1:
                split_3.append(split_1.pop(0))
            elif split_2:
                split_3.append(split_2.pop(0))

        return split_1, split_2, split_3

    split_1, split_2, split_3 = ensure_unique_rows(image_list)

    # Combine the splits ensuring no consecutive images with the same row_id
    combined_list = []
    prev_row_id = None

    while split_1 or split_2 or split_3:
        if split_1 and (prev_row_id is None or extract_image_number(split_1[0][0]) != prev_row_id):
            image = split_1.pop(0)
        elif split_2 and (prev_row_id is None or extract_image_number(split_2[0][0]) != prev_row_id):
            image = split_2.pop(0)
        elif split_3 and (prev_row_id is None or extract_image_number(split_3[0][0]) != prev_row_id):
            image = split_3.pop(0)
        else:
            # If all splits have the same row_id as the previous image, pop from the split with the longest distance
            if split_1 and len(split_1) >= len(split_2) and len(split_1) >= len(split_3):
                image = split_1.pop(0)
            elif split_2 and len(split_2) >= len(split_1) and len(split_2) >= len(split_3):
                image = split_2.pop(0)
            else:
                image = split_3.pop(0)
        
        prev_row_id = extract_image_number(image[0])
        combined_list.append(image)

    # Add a column indicating whether each image is shown first, second, or third
    row_order = {}
    for idx, image in enumerate(combined_list):
        row_id = extract_image_number(image[0])
        if row_id not in row_order:
            row_order[row_id] = 0
        row_order[row_id] += 1

        if row_order[row_id] == 1:
            order = 'first'
        elif row_order[row_id] == 2:
            order = 'second'
        else:
            order = 'third'

        combined_list[idx] = image + (order,)

    return combined_list

def split_and_save(image_list, participant_id, output_dir):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Calculate the number of rows per part
    rows_per_part = 15
    total_parts = 5

    # Split and save each part
    for part_num in range(total_parts):
        start_index = part_num * rows_per_part
        end_index = (part_num + 1) * rows_per_part

        part_df = pd.DataFrame(image_list[start_index:end_index], columns=['Image', 'Category', 'Source', 'Order'])

        part_df.to_csv(os.path.join(output_dir, f'randomized_{participant_id}_part{part_num + 1}.csv'), index=False)

# Load the CSV file
csv_path = os.path.join(base_dir,'image-list_v3-20240618.csv')
df = pd.read_csv(csv_path)

# Define the subject ID and participant ID
subject_id = subj_id
output_dir = os.path.join(base_dir, 'logs', subject_id, 'image_lists')

# Randomize the images
randomized_images = randomize_images(df, subject_id)

# Split and save the randomized images
split_and_save(randomized_images, subject_id, output_dir)

print(f'Randomized images have been saved to {output_dir}')

# initialize ratings, fixation, sample images
# Initialize fixation cross
fixation = visual.TextStim(win, text='+', height=75, color="yellow")

# images
negative = os.path.join(base_dir, 'study1-images_v1-20240602', '1271.jpg')
neutral = os.path.join(base_dir, 'study1-images_v1-20240602', '7180.jpg')
positive = os.path.join(base_dir, 'study1-images_v1-20240602', '2032.jpg')

images = [negative, positive, neutral]
random.shuffle(images)

# Function to generate fixation times following an exponential distribution
# not gonna use this, just gonna keep it normal
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

# initialize timer
timer = core.Clock()

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
                        

press2continue = visual.TextStim(win, text="Press any key to continue.", height=35, name='press2continue', pos=(0,vertical_positions[3]-155), anchorVert='bottom')

instr1 = visual.TextStim(win, text="""Welcome to the Images and Emotions Study. In this task, you will be viewing a series of images and providing ratings based on your responses to each one.

Before we begin, there are some important instructions to go over. We'll do that now. Please read them carefully to understand how to make your ratings.

As a reminder, some of the images you will see may be unpleasant or disturbing (similar what may be shown in an 'R' rated film). If you have any questions, please ask the researchers.""", height=35, name='Instruct 1', wrapWidth=875)

instr2 = visual.TextStim(win, text="""Before each image is presented, you will see a yellow fixation cross. Please focus on this cross and keep your head as still as possible. This helps us ensure accurate eye-tracking data.

After viewing each image, you will answer four questions about your response to the image.

Let's go over the instructions for each question.""", height=35, name='Instruct 2', wrapWidth=875)

instr3 = visual.TextStim(win, text="""How emotionally intense is this image?

We would like you to rate the image based on the amount of emotion it evokes. Focus on the intensity of the emotion, not whether it is good or bad.

For example, you might have two pictures: one depicting an athlete winning a gold medal (good) and one depicting an athlete getting injured and losing the race (bad). You can give them both the same ratings because they are both creating a similar level of emotion, even though the feelings are not the same.

Your answers should be based only on how much emotional intensity the picture captures. Not how the image makes you feel, or whether the image is positive or negative, good or bad.""", height=35, name='Instruct 3', wrapWidth=875)

instr4 = visual.TextStim(win, text="""The rating scale will look something like the slider below. Please use the full range of the scale rather than relying on just a few points. Remember, your rating should be based only on the emotional intensity, not on whether the image is positive or negative.

Use the right side of the scale if the image evokes strong emotions. Words like aroused, alert, activated, charged, or energized may describe your feelings.

Use the left side of the scale if the image evokes weak emotions. Words like unaroused, slow, still, de-energized, calm, or peaceful may describe your feelings.

Use the middle of the scale if the image evokes moderate emotions.

    """, height=35, name='Instruct 4', wrapWidth=950)
    
exampleRatingScale1 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,100],
                                    labels=['\nnot strongly\nemotional','\nstrongly\nemotional'],
                                    scale='How emotionally intense is this image?',
                                    showAccept=True, mouseOnly=True, size=0.7, pos=(0, vertical_positions[3]-150),
                                    stretch=2.5, markerStart=50, acceptText='continue', showValue=False)
                                    
instr5 = visual.TextStim(win, text="""How positive or negative is this image?

We would like you to rate the image based on how positive or negative it is. Again, use the full range of the scale to make your responses.

Use the right side of the scale if the image is positive. Think of words like happy, satisfied, competent, proud, contented, or delighted. It doesn't matter what the specific picture is about, as long as it represents something positive or good.

Use the left side of the scale if the image is negative. Think of words like unhappy, upset, irritated, angry, sad, or depressed. It doesn't matter what the specific image is about, as long as it is something negative or bad.

Use the middle of the scale if the image is neutral, neither positive nor negative.""", height=35, name='Instruct 5', wrapWidth=1000, pos=(0,vertical_positions[0]-250))


exampleRatingScale2 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,50,100],
                                    labels=['\nvery\nnegative','\nneutral','\nvery\npositive'],
                                    scale='How positive or negative is this image?',
                                    showAccept=True, mouseOnly=True, size=0.7, pos=(0, vertical_positions[3]-150),
                                    stretch=2.5, markerStart=50, acceptText='continue', showValue=False)

instr6 = visual.TextStim(win, text="""How does this image make you feel?

For this question, rate the images based on your personal emotional response. Use the full range of the scale to reflect your true feelings.

Use the right side of the scale if the image makes you feel positive emotions. Words like happy, satisfied, competent, proud, contented, or delighted may describe your feelings.

Use the left side of the scale if the image image makes you feel negative emotions. Words like unhappy, upset, irritated, angry, sad, or depressed may describe your feelings.

Use the middle of the scale if the image makes you feel neutral.""", height=35, name='Instruct 6', wrapWidth=1000, pos=(0,vertical_positions[0]-250))


exampleRatingScale3 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,100],
                                    labels=['\nvery \nnegative','\nvery\npositive'],
                                    scale='How does this image make you feel?',
                                    showAccept=True, mouseOnly=True, size=0.7, pos=(0, vertical_positions[3]-150),
                                    stretch=2.5, markerStart=50, acceptText='continue', showValue=False)
                                    

instr7 = visual.TextStim(win, text="""How exciting is this image?

Rate the images based on how excited or aroused they make you feel. Your ratings shold reflect the intensity of the emotion, not whether the image is good or bad.

Think back to our earlier example about the two images: one of a athlete winning a gold medal (something good) and one of an athlete getting injured and losing (something bad). You can give both images the same rating because they are both creating a similar level of emotion, even though the feelings are not the same.

We would like to know how intense the feeling is that the picture evokes; whether it is good or bad doesn't matter.
""", height=35, name='Instruct 7', wrapWidth=875)

instr8 = visual.TextStim(win, text="""The rating scale will look something like the slider below. Use the full range of the scale.

Use the right side of the scale if the image makes you feel emotionally aroused, alert, activated, charged, or energized.

Use the left side of the scale if the image makes you feel no emotional arousal, that is, if it makes you feel unaroused, slow, still, de-energized, calm, or peaceful.
 
Use the middle of the scale if the image makes you feel moderately aroused.""", height=35, name='Instruct 8', wrapWidth=950)


exampleRatingScale4 = visual.RatingScale(win, low=0, high=100, marker='slider', tickMarks=[0,50,100],
                                    labels=['\nnot at all\nexciting','\nmoderately\nexciting','\nvery\nexciting'],
                                    scale='How exciting is this image?',
                                    showAccept=True, mouseOnly=True, size=0.7, pos=(0, vertical_positions[3]-125),
                                    stretch=2.5, markerStart=50, acceptText='continue', showValue=False)

instr9 = visual.TextStim(win, text="""Before starting the actual task, you will practice rating three different images. This will help you get comfortable with the process and give you time to ask any questions.

Please remember to focus on the yellow fixation cross before each image appears and remember to keep your head as still as possible.

Press any key to begin the practice session.
""", height=35, name='Instruct 9', wrapWidth=875)

win.mouseVisible = False

spaceToStart = visual.TextStim(win, text='Press [i] to continue.', color='white')#, height=100)
spaceToStart.draw()
win.flip()
event.waitKeys(keyList=('i'))

# display instructions
win.mouseVisible = False
instr1.draw()
press2continue.draw()
win.flip()

event.waitKeys()

win.mouseVisible = False
instr2.draw()
press2continue.draw()
win.flip()

event.waitKeys()

win.mouseVisible = False
instr3.draw()
press2continue.draw()
win.flip()

event.waitKeys()

while exampleRatingScale1.noResponse:
    win.mouseVisible = True
    instr4.draw()
    exampleRatingScale1.draw()
    win.flip()

while exampleRatingScale2.noResponse:
    win.mouseVisible = True
    instr5.draw()
    exampleRatingScale2.draw()
    win.flip()

while exampleRatingScale3.noResponse:
    win.mouseVisible = True
    instr6.draw()
    exampleRatingScale3.draw()
    win.flip()

win.mouseVisible = False

instr7.draw()
press2continue.draw()
win.flip()

event.waitKeys()

while exampleRatingScale4.noResponse:
    win.mouseVisible = True
    instr8.draw()
    exampleRatingScale4.draw()
    win.flip()

win.mouseVisible = False

instr9.draw()
win.flip()
event.waitKeys()

# practice session
# main task:
for image in images:
    
    event.clearEvents()
    
    # Show fixation cross
    win.mouseVisible = False
    fixation.pos = random_position()
    fixation_time = generate_display_time(amount=3)
    fixation_time = np.clip(fixation_time, 2.75, 6)  # Ensure display time is between 2.75 and 6 seconds
    fixation.draw()
    win.flip()
    core.wait(fixation_time) # i think core.wait should be fine for now
    win.mouseVisible = False
    
    event.clearEvents()

    # Display image
    display_time = generate_display_time(amount=5)
    display_time = np.clip(display_time, 5, 6)  # Ensure display time is between 5 and 6 seconds
    image = visual.ImageStim(win, image=image)#, size=(400, 300))
    win.mouseVisible = False
    image.draw()
    win.flip()
    core.wait(display_time)
    
    # Collect ratings

    timer.reset()
    event.clearEvents()
    
    while (myRatingScale1.noResponse or myRatingScale2.noResponse or myRatingScale3.noResponse or myRatingScale4.noResponse) and timer.getTime() < rating_max:
        win.mouseVisible = True
        submitRatings.draw()
        myRatingScale1.draw()
        myRatingScale2.draw()
        myRatingScale3.draw()
        myRatingScale4.draw()
        win.flip()
    
    win.mouseVisible = False
    myRatingScale1.reset()
    myRatingScale2.reset()
    myRatingScale3.reset()
    myRatingScale4.reset()

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