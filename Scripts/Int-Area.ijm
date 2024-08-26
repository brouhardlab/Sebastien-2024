Title=getTitle();
run("Duplicate...", "duplicate channels=1");
rename(Title+"-Tubb3");
selectWindow(Title);
run("Duplicate...", "duplicate channels=1");
rename(Title+"-Blur");
run("Gaussian Blur...", "sigma=10 scaled");
imageCalculator("Divide create 32-bit", Title+"-Tubb3",Title+"-Blur");
selectWindow("Result of "+Title+"-Tubb3");
run("Enhance Contrast", "saturated=0.35");
run("Enhance Contrast", "saturated=0.35");
run("Gaussian Blur...", "sigma=1 scaled");
setAutoThreshold("Otsu dark");
//run("Threshold...");
setOption("BlackBackground", false);
run("Convert to Mask");
run("Analyze Particles...", "size=50-Infinity circularity=0 add");
count = roiManager("count");
array = newArray(count);
  for (i=0; i<array.length; i++) {
      array[i] = i;
  }
roiManager("select", array);
roiManager("combine");
roiManager("add");
roiManager("select", array);
roiManager("delete");
selectWindow(Title);
roiManager("Select", 0);
roiManager("multi-measure measure_all one append");
roiManager("reset");