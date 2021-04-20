import os
import threading

# qt
from qt_gui.plugin import Plugin
from python_qt_binding import loadUi
from python_qt_binding.QtWidgets import QWidget, QComboBox, QPushButton, QLabel

# ROS
from ament_index_python.packages import get_package_share_directory
import rclpy
from eufs_msgs.msg import CanState
from std_srvs.srv import Trigger


class RosCanGUI(Plugin):

    def __init__(self, context):
        super(RosCanGUI, self).__init__(context)
        self.setObjectName('RosCanSimGUI')

        self.node = context.node

        # Create QWidget
        self._widget = QWidget()
        # Get path to UI file which is a sibling of this file
        ui_file = os.path.join(get_package_share_directory('ros_can_sim'), 'resource',
                               'RosCanSimGUI.ui')
        # Extend the widget with all attributes and children from UI file
        loadUi(ui_file, self._widget)
        self._widget.setObjectName('RosCanSimUi')

        # Show _widget.windowTitle on left-top of each plugin (when
        # it's set in _widget). This is useful when you open multiple
        # plugins at once. Also if you open multiple instances of your
        # plugin at once, these lines add number to make it easy to
        # tell from pane to pane.
        if context.serial_number() > 1:
            self._widget.setWindowTitle(
                self._widget.windowTitle() + (' (%d)' % context.serial_number()))

        # setup states and missions
        # enumrations taken from CanState.msg
        self.states = {CanState.AS_OFF: "OFF",
                       CanState.AS_READY: "READY",
                       CanState.AS_DRIVING: "DRIVING",
                       CanState.AS_EMERGENCY_BRAKE: "EMERGENCY",
                       CanState.AS_FINISHED: "FINISHED"}

        self.missions = {CanState.AMI_NOT_SELECTED: "NOT_SELECTED",
                         CanState.AMI_ACCELERATION: "ACCELERATION",
                         CanState.AMI_SKIDPAD: "SKIDPAD",
                         CanState.AMI_AUTOCROSS: "AUTOCROSS",
                         CanState.AMI_TRACK_DRIVE: "TRACK_DRIVE",
                         CanState.AMI_AUTONOMOUS_DEMO: "AUTONOMOUS_DEMO",
                         CanState.AMI_ADS_INSPECTION: "ADS_INSPECTION",
                         CanState.AMI_ADS_EBS: "ADS_EBS",
                         CanState.AMI_DDT_INSPECTION_A: "DDT_INSPECTION_A",
                         CanState.AMI_DDT_INSPECTION_B: "DDT_INSPECTION_B",
                         CanState.AMI_JOYSTICK: "JOYSTICK",
                         CanState.AMI_MANUAL: "MANUAL"
        }   

        for mission in self.missions.values():
            self._widget.findChild(
                QComboBox, "MissionSelectMenu").addItem(mission)

        # hook up buttons to callbacks
        self._widget.findChild(
            QPushButton, "SetMissionButton").clicked.connect(self.setMission)
        self._widget.findChild(
            QPushButton, "ResetButton").clicked.connect(self.resetState)
        self._widget.findChild(
            QPushButton, "ResetSimButton").clicked.connect(self.resetSim)
        self._widget.findChild(
            QPushButton, "RequestEBS").clicked.connect(self.requestEBS)
        self._widget.findChild(
            QPushButton, "DriveButton").clicked.connect(self.setManualDriving)

        # Subscribers
        self.state_sub = self.node.create_subscription(CanState, "/ros_can/state", self.stateCallback, 10)

        # Publishers
        self.set_mission_pub = self.node.create_publisher(CanState, "/ros_can/set_mission", 1)

        # Services
        self.ebs_srv = self.node.create_client(Trigger, "/ros_can/ebs")
        self.reset_srv = self.node.create_client(Trigger, "/ros_can/reset")
        self.reset_vehicle_pos_srv = self.node.create_client(Trigger, "/ros_can/reset_vehicle_pos")
        self.reset_cone_pos_srv = self.node.create_client(Trigger, "/ros_can/reset_cone_pos")

        # Add widget to the user interface
        context.add_widget(self._widget)

        thread = threading.Thread(target=self.ros_spin, daemon=True)
        thread.start()

    def ros_spin(self):
        rclpy.spin(self.node)

    def setMission(self):
        """Sends a mission request to the simulated ros_can
        The mission request is of message type eufs_msgs/CanState
        where only the ami_mission field is used"""
        mission = self._widget.findChild(
            QComboBox, "MissionSelectMenu").currentText()

        self.node.get_logger().debug("Sending mission request for " + str(mission))

        # create message to be sent
        mission_msg = CanState()

        # find enumerated mission and set
        for enum, mission_name in self.missions.items():
            if mission_name == mission:
                mission_msg.ami_state = enum

        self.set_mission_pub.publish(mission_msg)
        self.node.get_logger().debug("Mission request sent successfully")

    def setManualDriving(self):
        # Change selected dropdown item to MANUAL
        self._widget.findChild(
            QComboBox, "MissionSelectMenu").setCurrentText(self.missions[CanState.AMI_MANUAL])
        self.setMission()

    def resetState(self):
        """Requests ros_can to reset its state machine"""
        self.node.get_logger().debug("Requesting ros_can_sim reset")

        if self.reset_srv.wait_for_service(timeout_sec=1):
            request = Trigger.Request()
            result = self.reset_srv.call_async(request)
            self.node.get_logger().debug("ros_can_sim reset successful")
            self.node.get_logger().debug(result)
        else:
            self.node.get_logger().warn("/ros_can/reset service is not available")

    def resetVehiclePos(self):
        """Requests vehicle_model to reset its position"""
        self.node.get_logger().debug("Requesting vehicle_model position reset")

        if self.reset_vehicle_pos_srv.wait_for_service(timeout_sec=1):
            request = Trigger.Request()
            result = self.reset_vehicle_pos_srv.call_async(request)
            self.node.get_logger().debug("Vehicle position reset successful")
            self.node.get_logger().debug(result)
        else:
            self.node.get_logger().warn("/ros_can/reset_vehicle_pos service is not available")

    def resetConePos(self):
        """Requests gazebo_cone_ground_truth to reset cone position"""
        self.node.get_logger().debug("Requesting gazebo_cone_ground_truth cone position reset")

        if self.reset_cone_pos_srv.wait_for_service(timeout_sec=1):
            request = Trigger.Request()
            result = self.reset_cone_pos_srv.call_async(request)
            self.node.get_logger().debug("Cone position reset successful")
            self.node.get_logger().debug(result)
        else:
            self.node.get_logger().warn("/ros_can/reset_cone_pos service is not available")

    def resetSim(self):
        """Requests state machine, vehicle position and cone position reset"""
        self.node.get_logger().debug("Requesting Simulation Reset")

        #Reset State Machine
        self.resetState()

        #Reset Vehicle Position
        self.resetVehiclePos()

        #Reset Cone Position
        self.resetConePos()

    def requestEBS(self):
        """Requests ros_can to go into EMERGENCY_BRAKE state"""
        self.node.get_logger().debug("Requesting ros_can_sim reset")

        if self.ebs_srv.wait_for_service(timeout_sec=1):
            request = Trigger.Request()
            result = self.ebs_srv.call_async(request)
            self.node.get_logger().debug("ros_can_sim reset successful")
            self.node.get_logger().debug(result)
        else:
            self.node.get_logger().warn("/ros_can/ebs service is not available")

    def stateCallback(self, msg):
        """Reads the ros_can state from the message
        and displays it within the GUI

        Args:
            msg (eufs_msgs/CanState): state of ros_can
        """
        self._widget.findChild(QLabel, "StateDisplay").setText(
            "Manual Driving" if msg.ami_state == CanState.AMI_MANUAL else self.states[msg.as_state])
        self._widget.findChild(QLabel, "MissionDisplay").setText(
            self.missions[msg.ami_state])

    def shutdown_plugin(self):
        """stop all publisher, subscriber and services
        necessary for clean shutdown"""
        self.set_mission_pub.destroy()
        self.state_sub.destroy()
        self.ebs_srv.destroy()
        self.reset_srv.destroy()

    def save_settings(self, plugin_settings, instance_settings):
        # don't know how to use
        # don't delete function as it breaks rqt
        pass

    def restore_settings(self, plugin_settings, instance_settings):
        # don't know how to use
        # don't delete function as it breaks rqt
        pass
