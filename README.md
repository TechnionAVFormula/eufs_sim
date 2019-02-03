# EUFS Autonomous Simulation

ROS/Gazebo simulation packages for driverless FSAE vehicles.

![simulation](https://eufs.eusa.ed.ac.uk/wp-content/uploads/2018/05/eufsa-sim.jpg)

### Contents
1. [Install Prerequisites](#requirements)
2. [Compiling and running](#compiling)
3. [Sensors](#sensors)
4. [Using The Gui](#guiuse)
5. [What's New?](#newstuff)

## Setup Instructions
### 1. Install Prerequisites <a name="requirements"></a>
##### - Install Ubuntu 16.04 LTS
##### - Install [ros-kinetic-desktop-full](http://wiki.ros.org/kinetic/Installation)
##### - Install ROS packages:
* ros-kinetic-ackermann-msgs
* ros-kinetic-twist-mux
* ros-kinetic-joy
* ros-kinetic-controller-manager
* ros-kinetic-robotnik-msgs
* ros-kinetic-velodyne-simulator
* ros-kinetic-effort-controllers
* ros-kinetic-velocity-controllers
* ros-kinetic-joint-state-controller
* ros-kinetic-gazebo-ros-control

Or if you are lazy like my here's a one-liner
```
sudo apt-get install ros-kinetic-ackermann-msgs ros-kinetic-twist-mux ros-kinetic-joy ros-kinetic-controller-manager ros-kinetic-robotnik-msgs ros-kinetic-velodyne-simulator ros-kinetic-effort-controllers ros-kinetic-velocity-controllers ros-kinetic-joint-state-controller ros-kinetic-gazebo-ros-control ros-kinetic-robotnik-msgs
```


### 2. Compiling and running <a name="compiling"></a>

Create a workspace for the simulation if you don't have one:
```mkdir -p ~/ros/eufs_ws/src```
Copy the contents of this repository to the `src` folder you just created.

Navigate to your workspace and build the simulation:
```
cd ~/ros/eufs_ws
catkin_make
```
_Note:_ You can use `catkin build` instead of `catkin_make` if you know what you are doing.

To enable ROS to find the EUFS packages you also need to run
```source /devel/setup.bash```
_Note:_ source needs to be run on each new terminal you open. You can also include it in your `.bashrc` file.

Now you can finally run our kickass simulation!!
```roslaunch eufs_gazebo small_track.launch```

An easy way to control the car is via
```roslaunch robot_control rqt_robot_control.launch```

### 3. Additional sensors <a name="sensors"></a>
Additional sensors for testing are avilable via the `ros-kinetic-robotnik-sensor` package. Some of them are already defined in `eufs_description/robots/eufs.urdf.xarco`. You can simply commment them in and attach them appropriately to the car.


**Sensor suit of the car by default:**

* VLP16 lidar
* ZED Stereo camera
* IMU
* GPS
* odometry

### 4. Using The Gui <a name="guiuse"></a>

First, open two terminals and enter the eufs_ws workspace.  In the first terminal, type
```roscore```

We are now done with that terminal - don't close it, but you can hide it wherever you'd like.  This only needs to be done once,
and after that you can run and close the gui as much as you'd like using the following instructions in the second terminal:

As always, type
```source ./devel/setup.bash```

To launch the gui, first try:
```rqt --standalone eufs_launcher```

If it does not find the plugin, try the following:
```rqt --force-discover```

The plugin is called "eufs_launcher" - you can find it on the drop-down menu after launching force-discover:

![Force-Discover Help](https://imgur.com/hzYuVVn.png)

When it works you shold have something like this:

![Full Gui](https://imgur.com/OcoBFUj.png)

For the most part, this should be self explanatory - the exception being perhaps the generation, noise, and image stuff.

The three buttons on the bottom are all launch buttons - the leftmost will launch whichever track you selected in the top-drop down bar.  
The rightmost will read in the selected image and turn it into a track, launching it immediately.
The middle will generate a random track image and then convert & launch it.  You can see the intermediate image in `eufs_gazebo/randgen_imgs`

The middle and right buttons are also sensitive to a new parameter called "noise" - these are randomly placed objects to the side of the track that the
car's sensors may pick up, mimicking real-world 'noise' from the environment.  By default this is off, but you can drag the slider to adjust it to whatever levels you desire.

More information can be found in the README in eufs_launcher

### 5. What's New? <a name="newstuff"></a>

1. New gui launcher for quality of life [100%]
2. Option to have torque-controlled car [100%]
3. Optionally noisy environments (only with random and from-image tracks) [100%]
4. Random track generation [25%]
     
     4.1. Functional random image generation [100%]
    
     4.2. Distinguish between yellow and blue cones [0%]
     
     4.3. Have better spacing on cones [0%]
     
     4.4. Actually good random image generation [0%] :P
5. Track-From-Image [100%]
