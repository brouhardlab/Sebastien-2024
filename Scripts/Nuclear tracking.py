# @ File    (label = "Input directory", style = "directory") srcFile
# @ File    (label = "Output directory", style = "directory") dstFile
# @ String  (label = "File extension", value=".tif") ext
# @ String  (label = "File name contains", value = "") containString

# @ Boolean(label = "Subpixel Localization", value = "true") subpixel_localization
# @ Boolean(label = "Mean Filtering", value = "true") mean_filtering
# @ Float(label = "Radius",  value = 0.01250) radius
# @ Integer(label = "Target Channel", value = 1) target_channel
# @ Boolean(label = "Threshold values from separate file?", value = "false") sep_thresh

# @ Boolean(label = "Allow Track Splitting", value = "false") track_splitting
# @ Boolean(label = "Allow Track Merging", value = "false") track_merging
# @ Boolean(label = "Allow Gap Closing", value = "true") gap_closing
# @ Float(label = "Gap Closing Max Distance ", value = 0.04) gap_max_distance
# @ Float(label = "Linking Max Distance", value = 0.04) linking_max_distance
# @ Integer(label = "Max Frame Gap", value = 2) max_frame_gap


import os
import sys
import csv

from ij import IJ, ImagePlus
from ij.gui import GenericDialog
from java.io import File

from fiji.plugin.trackmate import Model, Settings, TrackMate, SelectionModel, Logger
from fiji.plugin.trackmate.io import TmXmlWriter
from fiji.plugin.trackmate.detection import LogDetectorFactory
from fiji.plugin.trackmate.tracking.jaqaman import SparseLAPTrackerFactory
from fiji.plugin.trackmate.gui.displaysettings import DisplaySettingsIO
from fiji.plugin.trackmate.visualization.hyperstack import HyperStackDisplayer
from fiji.plugin.trackmate.features.track import (
    TrackDurationAnalyzer,
    TrackSpeedStatisticsAnalyzer,
    TrackBranchingAnalyzer,
)
from fiji.plugin.trackmate.action import ExportTracksToXML



# We have to do the following to avoid errors with UTF8 chars generated in
# TrackMate that will mess with our Fiji Jython.
reload(sys)
sys.setdefaultencoding("utf-8")


def run():
    srcDir = srcFile.getAbsolutePath()
    dstDir = dstFile.getAbsolutePath()
    filenames = []
    thresholds = []

    # obtain threshold value or file containing threshold values
    gd = GenericDialog("Threshold")
    if not sep_thresh:
        gd.addNumericField("Threshold", 5, 3)
        gd.showDialog()
        threshold = gd.getNextNumber()
        thresholds = 0
        print(threshold)
    else:
        gd.addStringField("Threshold file name (.csv)", "thresholds.csv", 50)
        gd.showDialog()
        threshold_file = gd.getNextString()
        threshold = "none"
        f = open(os.path.join(srcDir, threshold_file))
        lines = csv.reader(f, delimiter=",")
        print(lines)
        for x in lines:
            filenames.append(x[0])
            thresholds.append(x[1])
    for root, directories, filenames in os.walk(srcDir):
        filenames.sort()
        for filename in filenames:
            # Check for file extension
            if not filename.endswith(ext):
                continue
            # Check for file name pattern
            if containString not in filename:
                continue
            print(filenames)
            process(srcDir, dstDir, root, filename, threshold, filenames, thresholds)


def process(srcDir, dstDir, currentDir, fileName, threshold, filenames, thresholds):
    print("Processing:")

    # Opening the image
    print("Open image file", fileName)
    imp = ImagePlus(os.path.join(srcDir, fileName))
    name = str(fileName[0 : len(fileName) - 4])
    if threshold == "none":
        thresh_index = [filenames.index(i) for i in filenames if name in i]
        threshold = float(thresholds[thresh_index[0]])

    if not (os.path.isdir(dstDir)):
        os.mkdir(dstDir)

    # Switch t and z if necessary
    dims = imp.getDimensions()
    if dims[4] == 1:
        imp.setDimensions(dims[2], dims[4], dims[3])

    # ----------------------------
    # Create the model object
    # ----------------------------

    # Create and empty model to store parameters
    model = Model()

    # Send all messages to ImageJ log window.
    model.setLogger(Logger.IJ_LOGGER)

    # ------------------------
    # Prepare settings object
    # ------------------------

    settings = Settings(imp)

    # Configure detector - These values can be customized
    settings.detectorFactory = LogDetectorFactory()
    settings.detectorSettings = {
        "DO_SUBPIXEL_LOCALIZATION": subpixel_localization,
        "RADIUS": radius,
        "TARGET_CHANNEL": target_channel,
        "THRESHOLD": threshold,
        "DO_MEDIAN_FILTERING": mean_filtering,
    }

    # Configure tracker - These values can be customized
    # SimpleSparseLAP Tracker is used so merging and splitting are disabled
    settings.trackerFactory = SparseLAPTrackerFactory()
    settings.trackerSettings = (
        settings.trackerFactory.getDefaultSettings()
    )  # almost good enough
    settings.trackerSettings["ALLOW_TRACK_SPLITTING"] = track_splitting
    settings.trackerSettings["ALLOW_TRACK_MERGING"] = track_merging
    settings.trackerSettings["ALLOW_GAP_CLOSING"] = gap_closing
    settings.trackerSettings["GAP_CLOSING_MAX_DISTANCE"] = gap_max_distance
    settings.trackerSettings["MAX_FRAME_GAP"] = max_frame_gap
    settings.trackerSettings["LINKING_MAX_DISTANCE"] = linking_max_distance

    # Add ALL the feature analyzers known to TrackMate. They will
    # yield numerical features for the results, such as speed, mean intensity etc.
    settings.addAllAnalyzers()
    settings.addTrackAnalyzer(TrackDurationAnalyzer())
    settings.addTrackAnalyzer(TrackSpeedStatisticsAnalyzer())
    settings.addTrackAnalyzer(TrackBranchingAnalyzer())

    # -------------------
    # Instantiate plugin
    # -------------------

    trackmate = TrackMate(model, settings)

    # --------
    # Process
    # --------

    ok = trackmate.checkInput()
    if not ok:
        sys.exit(str(trackmate.getErrorMessage()))

    ok = trackmate.process()
    if not ok:
        sys.exit(str(trackmate.getErrorMessage()))

    outFile = File(dstDir, name + "_exportTracks.xml")
    ExportTracksToXML.export(model, settings, outFile)

    outFile = File(dstDir, name + "_exportModel.xml")
    writer = TmXmlWriter(outFile)
    writer.appendModel(model)
    writer.appendSettings(settings)
    writer.writeToFile()
    print("All Done!")

    # ----------------
    # Display results
    # ----------------

    # A selection.
    selectionModel = SelectionModel(model)

    # Read the default display settings.

    ds = DisplaySettingsIO.readUserDefault()
    displayer = HyperStackDisplayer(model, selectionModel, imp, ds)
    displayer.render()
    displayer.refresh()

    # The feature model, that stores edge and track features.
    fm = model.getFeatureModel()

    csv_file = open(dstDir + "/" + name + "_TrackStats.csv", "w")
    writer1 = csv.writer(csv_file)
    writer1.writerow(
        [
            "track #",
            "TRACK_MEAN_SPEED (pixel.frames)",
            "TRACK_MAX_SPEED (pixel.frames)",
            "NUMBER_SPLITS",
            "TRACK_DURATION (frames)",
            "TRACK_DISPLACEMENT (pixels)",
            "TOTAL_DISTANCE_TRAVELED (pixels)",
            "CONFINEMENT_RATIO",
        ]
    )

    # with open(dstDir+name+'_spots_properties.csv', "w") as trackfile:
    # with open(dstDir+name+'spots_properties.csv',"w") as trackfile:
    #   writer2 = csv.writer(trackfile)
    #   writer2.writerow(["spot ID","POSITION_X","POSITION_Y","Track ID", "FRAME"])
    #   writer2.writerow(["Tracking ID","Timepoint","X pos", "Y pos"])

    for id in model.getTrackModel().trackIDs(True):

        # Fetch the track feature from the feature model.
        # 'TRACK_ID','TRACK_DURATION','TRACK_DISPLACEMENT', 'TRACK_MEAN_SPEED', 'TOTAL_DISTANCE_TRAVELED', 'CONFINMENT_RATIO'
        v = fm.getTrackFeature(id, "TRACK_MEAN_SPEED")
        ms = fm.getTrackFeature(id, "TRACK_MAX_SPEED")
        d = fm.getTrackFeature(id, "TRACK_DURATION")
        s = fm.getTrackFeature(id, "NUMBER_SPLITS")
        d = fm.getTrackFeature(id, "TRACK_DURATION")
        e = fm.getTrackFeature(id, "TRACK_DISPLACEMENT")
        tdt = fm.getTrackFeature(id, "TOTAL_DISTANCE_TRAVELED")
        cr = fm.getTrackFeature(id, "CONFINEMENT_RATIO")
        writer1.writerow(
            [str(id), str(v), str(ms), str(s), str(d), str(e), str(tdt), str(cr)]
        )

        model.getLogger().log("")
        model.getLogger().log(
            "Track {}: mean velocity = {} {}/{}".format(
                id, v, model.getSpaceUnits(), model.getTimeUnits()
            )
        )

        track = model.getTrackModel().trackSpots(id)

        for spot in track:
            sid = spot.ID()
            x = spot.getFeature("POSITION_X")
            y = spot.getFeature("POSITION_Y")
            z = spot.getFeature("TRACK_ID")
            t = spot.getFeature("FRAME")
            q = spot.getFeature("QUALITY")
            snr = spot.getFeature("SNR_CH1")
            mean = spot.getFeature("MEAN_INTENSITY_CH1")
            model.getLogger().log(
                "Spot ID: {} at x={} y={} z={} t={} q={} snr={} mean={}".format(
                    sid, x, y, z, t, q, snr, mean
                )
            )

            # time= int(t) * int(Time_interval)
            # writer2.writerow([str(id), str(t), str(x), str(y)])
            # writer2.writerow([str(sid), str(x), str(y), str(id), str(t)])

    csv_file.close()
    # imp2 = WindowManager.getCurrentImage()
    # IJ.saveAs(capture, "tiff", os.path.join(dstDir,name, name + "_ImgOverlay.tif")) #specify file name
    IJ.run("Close")


run()