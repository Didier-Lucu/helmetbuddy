import sys
import speech_recognition as sr

def findMic():

    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print("Microphone with name \"{1}\" found for `Microphone(device_index={0})`".format(index, name))

    while (True):
        index = input("Please input index of desired device.")
        confirmation = input(f"You entered: '{index}'. Is this correct? (yes(y)/no(n)): ").strip().lower()
        if confirmation in ['yes', 'y']:
            print("Input confirmed.")
            return index
        elif confirmation in ['no', 'n']:
            print("Let's try again.")
        else:
            print("Please respond with 'yes' or 'no'.")
        


def calibrate():
    pass

def options():
    print("Options: \nfindmic \ncalibrate")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "findmic":
            findMic()
        elif sys.argv[1] == "calibrate":
            calibrate()
        elif sys.argv[1] == "help":
            options()
        
        else:
            options()
    else:
        print("Please select one of the following:")
        options()
