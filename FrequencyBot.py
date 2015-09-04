from Tkinter import *
from midiutil.MidiFile import MIDIFile
import random, tkMessageBox, os, json, tkFileDialog


VERSION = 1.1

# this is for tooltips
class ToolTipManager:

    label = None
    window = None
    active = 0

    def __init__(self):
        self.tag = None

    def getcontroller(self, widget):
        if self.tag is None:

            self.tag = "ui_tooltip_%d" % id(self)
            widget.bind_class(self.tag, "<Enter>", self.enter)
            widget.bind_class(self.tag, "<Leave>", self.leave)

            # pick suitable colors for tooltips
            try:
                self.bg = "systeminfobackground"
                self.fg = "systeminfotext"
                widget.winfo_rgb(self.fg) # make sure system colors exist
                widget.winfo_rgb(self.bg)
            except:
                self.bg = "#ffffe0"
                self.fg = "black"

        return self.tag

    def register(self, widget, text):
        widget.ui_tooltip_text = text
        tags = list(widget.bindtags())
        tags.append(self.getcontroller(widget))
        widget.bindtags(tuple(tags))

    def unregister(self, widget):
        tags = list(widget.bindtags())
        tags.remove(self.getcontroller(widget))
        widget.bindtags(tuple(tags))

    # event handlers

    def enter(self, event):
        widget = event.widget
        if not self.label:
            # create and hide balloon help window
            self.popup = Toplevel(bg=self.fg, bd=1)
            self.popup.overrideredirect(1)
            self.popup.withdraw()
            self.label = Label(
                self.popup, fg=self.fg, bg=self.bg, bd=0, padx=2
                )
            self.label.pack()
            self.active = 0
        self.xy = event.x_root + 16, event.y_root + 10
        self.event_xy = event.x, event.y
        self.after_id = widget.after(200, self.display, widget)

    def display(self, widget):
        if not self.active:
            # display balloon help window
            text = widget.ui_tooltip_text
            if callable(text):
                text = text(widget, self.event_xy)
            self.label.config(text=text)
            self.popup.deiconify()
            self.popup.lift()
            self.popup.geometry("+%d+%d" % self.xy)
            self.active = 1
            self.after_id = None

    def leave(self, event):
        widget = event.widget
        if self.active:
            self.popup.withdraw()
            self.active = 0
        if self.after_id:
            widget.after_cancel(self.after_id)
            self.after_id = None

_manager = ToolTipManager()

##
# Registers a tooltip for a given widget.
#
# @param widget The widget object.
# @param text The tooltip text.  This can be either a string, or a callable
#     object. If callable, it is called as text(widget) when the tooltip is
#     about to be displayed, and the returned text is displayed instead.

def register(widget, text):
    _manager.register(widget, text)

##
# Unregisters a tooltip.  Note that the tooltip information is automatically
# destroyed when the widget is destroyed.

def unregister(widget):
    _manager.unregister(widget)

class Application(Frame):

    # function that does all the work
    # origin:         the note that the scale is based on
    #                 it is an integer between 36 and 108
    # scaleType:      what kind of scale should the notes be chosen from
    #                 current options are "major", "minor", "mixolydian"
    # trackDuration:  how long should the whole track be
    #                 this should be a float in seconds
    # tempo:          how many beats per minute should the track be
    # maxRepeatPitch: the maximum number of times a given note can repeat (integer)
    # outputName:     what should the midi file be called.
    #                 ex. output.mid  
    # maxRests:       maximum number of rests between two notes (measured in beats)
    # maxDuration:    maximum duration of a given note (measured in beats)           
    def createScale(self, origin, scaleType, trackDuration, tempo, maxRepeatPitch, outputName, maxRests, maxDuration):
        # create your MIDI object
        mf = MIDIFile(1)     # only 1 track
        track = 0   # the only track

        time = 0    # start at the beginning
        mf.addTrackName(track, time, "Sample Track")
        mf.addTempo(track, time, tempo)
        channel = 0 # just the first channel
        volume = 100 # full volume
        pattern = self.scaleTypeOptions[scaleType]
        minPitch = 36 # no notes lower than this
        maxPitch = 108 # no notes higher than this
        
        trackDurationBeats = trackDuration * tempo / 60.0 # define track duration in beats

        
        ### define set of notes based on the scale and the origin note
        allNotes = [] # this is where notes will be added
        allNotes.append(origin) # add origin note
        
        # first add notes above the origin note
        currentNote = origin
        keepGoing = True
        while keepGoing:
            for p in pattern:
                currentNote += p
                if currentNote > maxPitch:
                    keepGoing = False
                    break
                allNotes.append(currentNote)  

        # now add notes lower than the origin note
        currentNote = origin
        keepGoing = True
        pattern.reverse()
        while keepGoing:
            for p in pattern:
                currentNote -= p
                if currentNote < minPitch:
                    keepGoing = False
                    break
                allNotes.append(currentNote)

        
        ### now actually create the track
        keepGoing = True
        thisIndex = 0 # this keeps track of where in the track we are (in beats)
        pitchRepeats = 0 # this keeps track of how many times the same pitch has repeated in a row
        durations = range(1, maxDuration + 1)
        rests = range(0, maxRests + 1)
        previousNote = 0 
        while keepGoing:
            thisNote = random.choice(allNotes)
            if(thisNote == previousNote):
                pitchRepeats += 1
            else:
                pitchRepeats = 0
            if pitchRepeats > maxRepeatPitch:
                continue

            thisDuration = random.choice(durations)
            thisRest = random.choice(rests)

            newIndex = thisIndex + thisRest + thisDuration
            if newIndex >= trackDurationBeats:
                keepGoing = False
                continue


            # add note
            mf.addNote(track, channel, thisNote, thisIndex, thisDuration, volume)
            # add rest
            mf.addNote(track, channel, thisNote, thisIndex + thisDuration, thisRest, 0)

            thisIndex = newIndex

            previousNote = thisNote


        # write it to disk
        with open(outputName, 'wb') as outf:
            mf.writeFile(outf)

    def run_program(self):
        scaleType = self.scaleTypeVariable.get()
        originKey = self.originPitchValue.get()
        originPitch = int(self.originKeys[originKey])
        trackDuration = int(self.trackDurationValue.get())
        tempo = int(self.tempoValue.get())
        maxPitchRepeats = int(self.maxPitchRepeatsValue.get())
        maxRestDuration = int(self.maxRestDurationValue.get())
        maxNoteDuration = int(self.maxNoteDurationValue.get())
        outputFilename = self.outputNameValue.get()

        self.createScale(originPitch, scaleType, trackDuration, tempo, maxPitchRepeats, outputFilename, maxRestDuration, maxNoteDuration)
        tkMessageBox.showinfo('Done', 'The midi file is saved at: ' + outputFilename)

    def deleteScale(self):
        thisScale = self.scaleTypeVariable.get()
        if(tkMessageBox.askyesno('Delete scale?', 'Are you sure you want to delete the ' + thisScale + ' scale?')):
            self.scaleTypeOptions.pop(thisScale)
            self.f.seek(0)
            self.f.truncate()
            json.dump(self.scaleTypeOptions, self.f)
            self.scaleTypeChooser["menu"].delete(0, END)
            for entry in self.scaleTypeOptions:
                self.scaleTypeChooser["menu"].add_command(label=entry, command=lambda temp=entry: self.scaleTypeVariable.set(temp))
            self.scaleTypeVariable.set(self.scaleTypeOptions.keys()[0])           

    def saveCustomScale(self):
        thisScaleName = self.defineScaleNameValue.get()
        thisScaleValueString = self.defineScaleValue.get()
        thisScaleValueString = thisScaleValueString.replace(' ', '').split(',')
        thisScaleValue = [int(tSVS) for tSVS in thisScaleValueString]
        self.scaleTypeOptions[thisScaleName] = thisScaleValue
        self.f.seek(0)
        self.f.truncate()
        json.dump(self.scaleTypeOptions, self.f)
        self.scaleTypeChooser["menu"].delete(0, END)
        for entry in self.scaleTypeOptions:
            self.scaleTypeChooser["menu"].add_command(label=entry, command=lambda temp=entry: self.scaleTypeVariable.set(temp))
        self.scaleTypeVariable.set(thisScaleName)
        tkMessageBox.showinfo('Done', 'The custom ' + thisScaleName + ' scale was saved.')

    def getDownloadPath(self):
        thisPath = tkFileDialog.askdirectory()
        if thisPath != '':
            self.outputNameEntry.configure(state=NORMAL)
            self.outputNameEntry.insert(0, thisPath+'/output.mid')

    def createWidgets(self):

        ##### 
        # first read the file with scales in it
        # if it is blank (or doesn't exist), write a generic one
        wd = os.path.abspath(os.path.dirname(sys.argv[0]))        
        try:
            self.f = open(wd + '/scales.txt', 'r+')
            self.scaleTypeOptions = json.load(self.f)
        except IOError:
            self.scaleTypeOptions = {
                'major': [2, 2, 1, 2, 2, 2, 1],
                'minor': [2, 1, 2, 2, 1, 3, 1],
                'mixolydian': [1, 2, 2, 2, 1, 2, 2]
            }
            self.f = open(wd + '/scales.txt', 'w')
            json.dump(self.scaleTypeOptions, self.f)

        ######
        # options to select scale type
        self.scaleTypeVariable = StringVar(self)
        self.scaleTypeChooser = apply(OptionMenu, (self, self.scaleTypeVariable) + tuple(self.scaleTypeOptions))
        self.scaleTypeChooser.grid(row=10, column=2)
        self.scaleTypeLabel = Label(self, text='Scale Type:')
        self.scaleTypeLabel.grid(row=10, column=1)
        self.scaleTypeDeleteButton = Button(self, text="Delete Scale", command=self.deleteScale)
        self.scaleTypeDeleteButton.grid(row=10, column=3)
        register(self.scaleTypeLabel, 'This is the type of scale used to generate all the possible notes that can be chosen.')


        #####
        # define custom scales
        self.FRAME1 = Frame(self)
        self.FRAME1.grid(row=15, column=1)
        self.FRAME2 = Frame(self)
        self.FRAME2.grid(row=15, column=2)
        self.defineScaleLabel = Label(self.FRAME1, text='Define Scale:')
        self.defineScaleLabel.grid(row=15, column=0)
        self.defineScaleValue = StringVar(self)
        self.defineScaleEntry = Entry(self.FRAME1, textvariable=self.defineScaleValue)
        self.defineScaleEntry.insert(0, '1, 1, 1, 1, 1, 1, 1')
        self.defineScaleEntry.grid(row=15, column=1)
        self.defineScaleNameLabel = Label(self.FRAME2, text = 'Name of Scale:')
        self.defineScaleNameLabel.grid(row=15, column=2)
        self.defineScaleNameValue = StringVar(self)
        self.defineScaleNameEntry = Entry(self.FRAME2, textvariable=self.defineScaleNameValue)
        self.defineScaleNameEntry.insert(0, 'default')
        self.defineScaleNameEntry.grid(row=15, column=3)
        self.defineScaleButton = Button(self, text="Save Scale", command=self.saveCustomScale)
        self.defineScaleButton.grid(row=15, column=3)
        register(self.defineScaleNameLabel, 'Here you can define a custom scale. Each value is a semitone step size. For example, the major scale would be "2, 2, 1, 2, 2, 2, 1"')
        register(self.defineScaleLabel, 'Here you can define a custom scale. Each value is a semitone step size. For example, the major scale would be "2, 2, 1, 2, 2, 2, 1"')


        #####
        # origin pitch
        self.originKeys = {
            "A" : 69,
            "A#": 70,
            "B" : 71,
            "C" : 60,
            "C#": 61,
            "D" : 62,
            "D#": 63,
            "E" : 64,
            "F" : 65,
            "F#": 66,
            "G" : 67,
            "G#": 68
        }
        self.originKeyKeys = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
        self.originPitchLabel = Label(self, text="Key:")
        self.originPitchLabel.grid(row=20, column=1)
        self.originPitchValue = StringVar(self)
        self.originPitchChooser = OptionMenu(self, self.originPitchValue, *self.originKeyKeys)
        self.originPitchChooser.grid(row=20, column=2)
        register(self.originPitchLabel, "This is the key that the notes will be in (the origin of the scale).")
        
        #####
        # track duration
        self.trackDurationLabel = Label(self, text="Track Duration:")
        self.trackDurationLabel.grid(row=30, column=1)
        self.trackDurationValue = StringVar(self)
        self.trackDurationSpin = Spinbox(self, from_=1, to=3600, textvariable=self.trackDurationValue)
        self.trackDurationSpin.delete(0, END)
        self.trackDurationSpin.insert(0, "120")
        self.trackDurationSpin.grid(row=30, column=2)
        register(self.trackDurationLabel, "How long should the final midi track be (in seconds)?")
        
        #####
        # tempo
        self.tempoLabel = Label(self, text="Beats Per Minute:")
        self.tempoLabel.grid(row=40, column=1)
        self.tempoValue = StringVar(self)
        self.tempoSpin = Spinbox(self, from_=1, to=3600, textvariable=self.tempoValue)
        self.tempoSpin.delete(0, END)
        self.tempoSpin.insert(0, "120")
        self.tempoSpin.grid(row=40, column=2)
        register(self.tempoLabel, "How many beats per minute should the midi track be?")
        
        #####
        # max pitch repeats
        self.maxPitchRepeatsLabel = Label(self, text="Max Same-Note Repeats:")
        self.maxPitchRepeatsLabel.grid(row=50, column=1)
        self.maxPitchRepeatsValue = StringVar(self)
        self.maxPitchRepeatsSpin = Spinbox(self, from_=0, to=3600, textvariable=self.maxPitchRepeatsValue)
        self.maxPitchRepeatsSpin.delete(0, END)
        self.maxPitchRepeatsSpin.insert(0, "3")
        self.maxPitchRepeatsSpin.grid(row=50, column=2)
        register(self.maxPitchRepeatsLabel, "This is the maximum number of times the same pitch can occur consecutively.")
        
        #####
        # max number beats per rest
        self.maxRestDurationLabel = Label(self, text="Max Rest Duration:")
        self.maxRestDurationLabel.grid(row=60, column=1)
        self.maxRestDurationValue = StringVar(self)
        self.maxRestDurationSpin = Spinbox(self, from_=0, to=3600, textvariable=self.maxRestDurationValue)
        self.maxRestDurationSpin.delete(0, END)
        self.maxRestDurationSpin.insert(0, "3")
        self.maxRestDurationSpin.grid(row=60, column=2)
        register(self.maxRestDurationLabel, "This is the maximum number of beats between notes.")
        
        #####
        # max note duration
        self.maxNoteDurationLabel = Label(self, text="Max Note Duration:")
        self.maxNoteDurationLabel.grid(row=70, column=1)
        self.maxNoteDurationValue = StringVar(self)
        self.maxNoteDurationSpin = Spinbox(self, from_=1, to=3600, textvariable=self.maxNoteDurationValue)
        self.maxNoteDurationSpin.delete(0, END)
        self.maxNoteDurationSpin.insert(0, "8")
        self.maxNoteDurationSpin.grid(row=70, column=2)
        register(self.maxNoteDurationLabel, "This is the maximum length of a note in beats.")
        
        #####
        # output filename
        self.outputNameButton = Button(self, text="Choose Output Directory", command=self.getDownloadPath)
        self.outputNameButton.grid(row=80, column=1)
        self.outputNameValue = StringVar(self)
        self.outputNameEntry = Entry(self, textvariable=self.outputNameValue, state=DISABLED)
        self.outputNameEntry.grid(row=80, column=2)
        register(self.outputNameButton, "First choose an output directory with this button, then you can edit the output filename in the box to the right.")
        
        ##### 
        # control buttons
        
        
        # quit button
        self.QUIT = Button(self)
        self.QUIT["text"] = "Quit"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit

        self.QUIT.grid(row=100, column=1)

        # other button
        self.run = Button(self)
        self.run["text"] = "Run",
        self.run["command"] = self.run_program

        self.run.grid(row=100, column=2)



    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()

root = Tk()
root.title('FrequencyBot v' + str(VERSION))
app = Application(master=root)
app.mainloop()
root.destroy()