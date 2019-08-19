import math
from PIL import Image
from PIL import ImageDraw
from random import randrange, uniform
import rospy
from scipy.special import binom
from LauncherUtilities import calculate_tangent_angle, cap_angle, cap_angle_odd, magnitude, normalize_vec
import numpy as np

"""
###############################################################################
###############################################################################
###############################################################################
###########################Track Generator Overview############################
###############################################################################
###############################################################################
###############################################################################
###########################Functions For Public Use############################
###############################################################################
#									      #
#	TrackGenerator.generate(values: List[float])                          #
#			-> Tuple[List[Tuple[float,float]],int,int]            #
#		Takes in a list of preset data.  Check out the get_presets()  #
#		function for a thorough and perpetually up to date list of    #
#		each piece of data.					      #
#		This returns a tuple of the form (xys,width,height), where:   #
#			xys:						      #
#				A list of points that outline the	      #
#				generated track.			      #
#			width:						      #
#				The width that is spanned by xys	      #
#			height:						      #
#				The height that is spanned by xys	      #
#		There will always be a margin of at least 5 on the returned   #
#		xys, so width and height are always at least 10 larger than   #
#		if the range was strictly calculated.			      #
#		This is done for the sake of ConversionTools' TrackImage      #
#		specification, which requires the margin.		      #
#									      #
#	TrackGenerator.get_presets()  -> List[Tuple[str,List[float]]]         #
#		Returns a list of all generator presets (the str in the tuple)#
#		coupled with their preset values (the list in the tuple)      #
#									      #
#	TrackGenerator.get_default_preset() -> str			      #
#		Returns the default preset (usually "Small Straights")        #
#									      #
#	TrackGenerator.get_preset_names() -> List[str]                        #
#		Returns a list of all the generator presets.                  #
#									      #
#	TrackGenerator.get_preset(name: str) -> List[float]		      #
#		Returns a list of all the preset data of the specified        #
#		preset (the one with the matching name).                      #
#									      #
###############################################################################
#                                                                             #
#	There are other functions available (many others), but they are not   #
#	necessarily meant for use outside this file.                          #
#									      #
#	That doesn't stop them from being used, of course - but depending on  #
#	the circumstances, their use implies that they maybe should be        #
#	factored out into a seperate library.				      #
#									      #
#	Since the LauncherModule/TrackGenerator/ConversionTools ecosystem is  #
#	still in a state of flux, function signatures for all functions but   #
#	the ones listed above are subject to change without warning.          #
#									      #
###############################################################################
"""


class TrackGenerator:

	#The rules for autocross:
	#	Straights: 		<=80 meters
	#	Constant Turns:		<=25 meter radius
	#	Hairpin Turns: 		>=4.5 meter outside radius
	#	Slalom: 		Cones in a straight line with 7.5 to 12 meter spacing [NOTE: can't be generated at this point, added later]
	#	Track Width: 		>=3 meters
	#	Track Length: 		<=1500 meters

	MIN_STRAIGHT = 20
	MAX_STRAIGHT = 80
	MIN_CONSTANT_TURN = 10
	MAX_CONSTANT_TURN = 25
	MIN_HAIRPIN = 4.5
	MAX_TRACK_LENGTH = 1500
	LAX_GENERATION = False
	TRACK_MODE = "Circle&Line"
	IGNORE_INTERSECTIONS = True #debugging parameter to stop generation from failing due to self-intersections
	DEBUG_INFO = True #debugging parameter to notify user when intersection fails

	def __init__(self):
		pass

	@staticmethod
	def get_presets():
		return [("Contest Rules",[
				10,#Min straight length
				80,#Max straight length
				10,#Min constant turn radius
				25,#Max constant turn radius
				4.5,#Min hairpin turn radius
				10,#Max hairpin turn radius
				3,#Max hairpin pairs amount
				1500,#Max length
				0,#Lax Generation (off)
				0#Circle&Line mode
			]),
			("Small Straights",[
				5,#Min straight length
				40,#Max straight length
				10,#Min constant turn radius
				25,#Max constant turn radius
				4.5,#Min hairpin turn radius
				10,#Max hairpin turn radius
				3,#Max hairpin pairs amount
				700,#Max length
				1,#Lax Generation (on)
				0#Circle&Line mode
			]),
			("Computer Friendly",[
				10,#Min straight length
				80,#Max straight length
				5,#Min constant turn radius
				15,#Max constant turn radius
				4.5,#Min hairpin turn radius
				10,#Max hairpin turn radius
				3,#Max hairpin pairs amount
				500,#Max length
				1,#Lax Generation (on)
				0#Circle&Line mode
			]),
			("Bezier",[
				10,#Min straight length
				80,#Max straight length
				5,#Min constant turn radius
				15,#Max constant turn radius
				4.5,#Min hairpin turn radius
				10,#Max hairpin turn radius
				3,#Max hairpin pairs amount
				500,#Max length
				1,#Lax Generation (on)
				1#Bezier mode
			])]

	@staticmethod
	def get_default_mode_string():
		return "Circle&Line"

	@staticmethod
	def get_default_mode_number():
		return TrackGenerator.get_number_from_mode(TrackGenerator.get_default_mode_string())

	@staticmethod
	def get_mode_from_number(num):
		if num==0: return "Circle&Line"
		elif num==1: return "Bezier"
		return "Circle&Line"

	@staticmethod
	def get_number_from_mode(mode):
		if mode=="Circle&Line": return 0
		elif mode == "Bezier": return 1
		return 0

	@staticmethod
	def get_default_preset():
		return "Small Straights"

	@staticmethod
	def get_preset_names():
		toReturn = []
		allPresets = TrackGenerator.get_presets()
		for a in allPresets:
			toReturn.append(a[0])
		return toReturn

	@staticmethod
	def get_preset(name):
		allPresets = TrackGenerator.get_presets()
		for a in allPresets:
			if a[0] == name:
				return a[1]
		rospy.logerr("No such preset: " + name)
		rospy.logerr("Defaulting to Contest Rules")
		return get_preset("Contest Rules")

	@staticmethod
	def set_preset(name):
		values = TrackGenerator.get_preset(name)
		TrackGenerator.set_data(values)
		

	@staticmethod
	def set_data(values):
		TrackGenerator.MIN_STRAIGHT = values[0]
		TrackGenerator.MAX_STRAIGHT = values[1]
		TrackGenerator.MIN_CONSTANT_TURN = values[2]
		TrackGenerator.MAX_CONSTANT_TURN = values[3]
		TrackGenerator.MIN_HAIRPIN = values[4]
		TrackGenerator.MAX_HAIRPIN = values[5]
		TrackGenerator.MAX_HAIRPIN_NUM = values[6]
		TrackGenerator.MIN_HAIRPIN_NUM = 1 if TrackGenerator.MAX_HAIRPIN_NUM > 0 else 0
		TrackGenerator.MAX_TRACK_LENGTH = values[7]
		TrackGenerator.LAX_GENERATION = values[8]==1
		TrackGenerator.TRACK_MODE = TrackGenerator.get_mode_from_number(values[9])

	@staticmethod
	def generate(values):
		#Generate the track as pure data
		#Returns a list of points to define the path of the track, along with a bounding width & height for how big the track is.
		#Input is a list of track parameters
		TrackGenerator.set_data(values)
		xys = []
		overlapped = False
		generateFunction = generate_autocross_trackdrive_track if TrackGenerator.TRACK_MODE == "Circle&Line" else generate_bezier_track
		while overlapped or xys==[]:
			#Re-generate if the track overlaps itself
			(xys,twidth,theight) = generateFunction((0,0))
			xys2 = [(int(x[0]),int(x[1])) for x in xys]
			xys2 = compactify_points(xys2)
			overlapped = check_if_overlap(xys2) and not TrackGenerator.IGNORE_INTERSECTIONS
			if overlapped:
				if TRACK_GENERATOR.DEBUG_INFO: rospy.logerr("Overlap check failed")
				print("Oops!  The track intersects itself too much.  Retrying...")
		rospy.logerr("Yalala")
		return (xys,twidth,theight)

	

"""
ESSENTIAL FUNCTIONS
"""

def generate_bezier_track(startpoint):
		#In this function we handle the quick&dirty Bezier generator
		xys = []

		goalpoints = [	(startpoint[0]+TrackGenerator.MAX_TRACK_LENGTH*0.08,startpoint[1]),
				(startpoint[0]+TrackGenerator.MAX_TRACK_LENGTH*0.12,startpoint[1]+TrackGenerator.MAX_TRACK_LENGTH*0.08),
				(startpoint[0]-TrackGenerator.MAX_TRACK_LENGTH*0.03,startpoint[1]+TrackGenerator.MAX_TRACK_LENGTH*0.12)]

		testBezier,intangent,outtangent = get_random_bezier(startpoint,goalpoints[0])
		xys.extend([testBezier(t*0.01) for t in range(0,101)])
		initialTangent = intangent

		prevtangent = outtangent
		for g in range(1,len(goalpoints)):
			testBezier,intangent,prevtangent = get_random_bezier(goalpoints[g-1],goalpoints[g],starttangent=prevtangent)
			xys.extend([testBezier(t*0.01) for t in range(0,101)])

		testBezier,intangent,prevtangent = get_random_bezier(goalpoints[-1],startpoint,starttangent=prevtangent,calculate_tangent_angle=initialTangent)
		xys.extend([testBezier(t*0.01) for t in range(0,101)])
		
		return convert_points_to_all_positive(xys)

def get_random_bezier(startpoint,endpoint,starttangent=None,calculate_tangent_angle=None,order=4):
		#For the math to work out, we need Beziers to be at least quartic
		starttangent = uniform(0,2*math.pi) if starttangent == None else starttangent
		calculate_tangent_angle   = uniform(0,2*math.pi) if calculate_tangent_angle   == None else calculate_tangent_angle

		#The incoming tangent is the same as the line from P0 to P1
		#Outgoing tangent is the same as the line from P(n-1) to P(n)
		#Where P0, P1, ..., P(n-1), P(n) are the control points
		#All other control points are free to be selected.
		scale = uniform(10,100)
		p0_to_p1 = (math.cos(starttangent)*scale,math.sin(starttangent)*scale)
		p0 = startpoint
		p1 = (p0[0]+p0_to_p1[0],p0[1]+p0_to_p1[1])

		scale = uniform(10,100)
		pn_1_to_pn = (math.cos(calculate_tangent_angle)*scale,math.sin(calculate_tangent_angle)*scale)
		pn = endpoint
		pn_1 = (pn[0]-pn_1_to_pn[0],pn[1]-pn_1_to_pn[1])

		controlpoints = [p0,p1,pn_1,pn]

		return (get_parametric_bezier(controlpoints),starttangent,calculate_tangent_angle)


def get_parametric_bezier(controlpoints):
		#This function will itself return a function of a parameterized bezier
		#That is, the result will be a function that takes a time parameter from 0 to 1
		#and traveling along it results in the points on the bezier.
		#I made this code match the Bezier curve definition on wikipedia as closely as
		#possible (Explicit definition, not the recursive one)
		def toReturn(cp,t):
			thesumx = 0
			thesumy = 0
			n = len(cp)
			for i in range(n):
				coefficient = binom(n-1,i) * (1-t)**(n-i-1) * t**i
				thesumx += coefficient * cp[i][0]
				thesumy += coefficient * cp[i][1]
			return (thesumx,thesumy)
		return lambda t: toReturn(controlpoints,t)

def generate_autocross_trackdrive_track(startpoint):
		#In this function we handle the traditional Circle&Line generator
		xys = []
		curTrackLength = 0
		curpoint = startpoint

		#Let's start with a small straght
		startangle = uniform(0,math.pi/8)
		(generated, curpoint, deltalength) = generate_straight(startpoint,TrackGenerator.MIN_STRAIGHT,startangle)
		curTrackLength += deltalength
		xys.extend(generated)

		#Now we want to set checkpoints to pass through:
		#The magic numbers here are effectively random.  They serve to make the track not follow an exact square.	
		#They could be replaced by a small random number generator, but since these numbers work well I wouldn't bother.
		goalpoints = [	(startpoint[0]+TrackGenerator.MAX_TRACK_LENGTH*0.08,startpoint[1]),
				(startpoint[0]+TrackGenerator.MAX_TRACK_LENGTH*0.12,startpoint[1]+TrackGenerator.MAX_TRACK_LENGTH*0.08),
				(startpoint[0]-TrackGenerator.MAX_TRACK_LENGTH*0.03,startpoint[1]+TrackGenerator.MAX_TRACK_LENGTH*0.12)]

		
		###Testing vvv
		testtan = uniform(0,2*math.pi)
		testcase = (100,0)
		(generated, curpoint, deltalength,outnormal) = \
			generate_constant_turn_until_facing_point(
				startpoint,
				50,
				testtan,
				testcase,
				(-math.sin(testtan),math.cos(testtan)),
				turnagainstnormal=True)
		curTrackLength += deltalength
		xys.extend(generated)
		xys.append(testcase)
		return convert_points_to_all_positive(xys)
		###Testing ^^^
		

		for goalpoint in goalpoints:
			(generated, curpoint, length) = generate_path_from_point_to_point(curpoint,goalpoint,calculate_tangent_angle(xys),fuzzradius=20)
			curTrackLength+= length
			xys.extend(generated)
			#Now let's do early-checking for overlaps
			test = compactify_points([(int(x[0]),int(x[1])) for x in xys])
			rospy.logerr("Yamaha 2000")
			if check_if_overlap(test) and not TrackGenerator.IGNORE_INTERSECTIONS: 
				if TrackGenerator.DEBUG_INFO: rospy.logerr("Early Overlap Checking: Failed")
				return (test,0,0)

		#Now lets head back to the start:
		#We're gonna set a checkpoint that is close but not exactly the start point
		#so that we have breathing room for the final manouever:
		rospy.logerr("Yamaha 2001")
		(generated, curpoint, length) = generate_path_from_point_to_point(curpoint,\
										(startpoint[0]-TrackGenerator.MAX_STRAIGHT*0.5,\
										startpoint[1]+TrackGenerator.MAX_CONSTANT_TURN*1.5),\
										calculate_tangent_angle(xys),fuzzradius=0)
		curTrackLength+= length
		xys.extend(generated)
		rospy.logerr("Yamaha 2002")
		#Now we will add a circle to point directly away from the startpoint
		goalTangent = (-math.cos(startangle),-math.sin(startangle))
		goalPoint = startpoint
		initialTangentAngle = calculate_tangent_angle(xys)
		initialTangent = (math.cos(initialTangentAngle),math.sin(initialTangentAngle))
		initialPoint = (xys[-1][0],xys[-1][1])
		outerTurnAngle = math.acos(  -initialTangent[0]*goalTangent[0] - initialTangent[1]*goalTangent[1]  )
		circleTurnAngle = math.pi - outerTurnAngle
		circleTurnPercent = circleTurnAngle / (2*math.pi)
		circleRadius = uniform(TrackGenerator.MIN_CONSTANT_TURN,TrackGenerator.MAX_CONSTANT_TURN)
		(generated,curpoint,length,outnormal) = generate_constant_turn(
								initialPoint,
								circleRadius,
								initialTangentAngle,
								circlepercent=circleTurnPercent,
								turnagainstnormal=True)
		curTrackLength+=length
		xys.extend(generated)
		rospy.logerr("Yamaha 2003")

		#Add a circle to turn 180 degrees to face the start point directly
		#Radius is calculated by finding distance when projected along the normal
		outnormal = normalize_vec(outnormal)
		diff = ( curpoint[0]-startpoint[0],curpoint[1]-startpoint[1] )
		circleRadius2 = (diff[0]*outnormal[0]+diff[1]*outnormal[1])/2
		(generated, curpoint, length, _) = generate_constant_turn(curpoint,circleRadius2,calculate_tangent_angle(xys),circlepercent=0.5,turnagainstnormal=True)
		curTrackLength+=length
		xys.extend(generated)
		rospy.logerr("Yamaha 2004")

		#Finally, add a straight to connect it to the start
		straightLength = magnitude( ( xys[-1][0] - startpoint[0], xys[-1][1] - startpoint[1] ) )*1.1
		(generated, curpoint, deltalength) = generate_straight(curpoint, straightLength ,calculate_tangent_angle(xys))
		curTrackLength += deltalength
		xys.extend(generated)
		rospy.logerr("Yamaha 2005")

		if not TrackGenerator.LAX_GENERATION:
			#Check if accidentally created too big of a straight
			if straightLength + TrackGenerator.MIN_STRAIGHT > TrackGenerator.MAX_STRAIGHT:
				#We always start each track with a minimum-length straight, which is joined up with the final straight,
				#hence the addition of MIN_STRAIGHT here.
				print("Track gen failed - couldn't connect ending and still follow the preset rules!  Retrying.")
				return generate_autocross_trackdrive_track(startpoint)
			elif curTrackLength > 1500:
				print("Track gen failed - track too long, oops!  Retrying.")
				return generate_autocross_trackdrive_track(startpoint)

		return convert_points_to_all_positive(xys)


def generate_path_from_point_to_point(startpoint,endpoint,intangent,depth=20,hairpined=False,manyhairpins=False,fuzzradius=0):
	#Here we want to get from a to b by randomly placing paths 
	#[Note: depth parameter is just to limit recursion overflows]
	#[And hairpined parameter prevents multiple hairpins - we should have at most
	#one or else its hard to generate nice paths]
	#[manyhairpins overrides this and allows an arbitrary amount]
	#[fuzzradius is how close to the end we want to be]
	length = 0
	points = []
	circleradius = uniform(TrackGenerator.MIN_CONSTANT_TURN,TrackGenerator.MAX_CONSTANT_TURN)

	#We want to know ahead of time which way the circle will turn - that way we don't get loopty-loops
	#where the circle turns nearly all the way around when it would have been better to have the center
	#on the other side.
	#We'll do this by calculating the normal we want.
	#First, we want to know the path from start to goal.
	#And more specifically, its angle
	directpathangle = calculate_tangent_angle([startpoint,endpoint])

	#Our circle code takes in "turnagainstnormal" - alternatively, this parameter is equivalent to passing in
	#a vector pointing TOWARDS the radius.  So let's calculate that!  If we have the goal be at a "higher" angle
	#than it, we want the radius to be up, otherwise down.  The angle of it pointing up is simply pi/2 higher than the tangent (90 degrees)
	normalangle = cap_angle(math.pi/2 + intangent)

	#We now calculate if we need to add an additional pi to it.
	#If directpathangle is higher than intangent - but how do we define higher?  We say that it is higher if the
	#counterclockwise angle difference is smaller than the clockwise difference.
	if cap_angle(directpathangle-normalangle)>cap_angle(directpathangle-directpathangle):
		normalangle = cap_angle(math.pi + normalangle)

	#Also flip it if tangent heading in 'negative' direction
	#if (abs(cap_angle_odd(intangent))math.pi/2):
	#	normalangle = cap_angle(math.pi + normalangle)

	#Finally lets convert this into a normal:
	thenormal = (1,math.tan(normalangle))

	#Now let's actually draw the circle!
	(generated, curpoint,deltalength,output_normal) = generate_constant_turn_until_facing_point(startpoint,circleradius,intangent,endpoint,thenormal)
	length += deltalength
	points.extend(generated)

	#Check if we're within MAX_STRAIGHT of the goal:
	(cx,cy) = points[-1]
	(ex,ey) = endpoint
	squaredistance = (ex-cx)*(ex-cx)+(ey-cy)*(ey-cy)
	#print("--------------------------------")
	#print(math.sqrt(squaredistance))
	#print(points[-1])
	#print(endpoint)
	#print("++++++++++++++++++++++++++++++++")
	if squaredistance <= TrackGenerator.MAX_STRAIGHT**2+fuzzradius**2:
		#We'll just draw a straight to it
		(generated, curpoint,deltalength) = generate_straight(points[-1],
								min(math.sqrt(squaredistance),TrackGenerator.MAX_STRAIGHT),
								calculate_tangent_angle(points))
		length += deltalength
		points.extend(generated)
	else:
		#Go as far as we can (unless we're very close in which case don't, because it'll cause the next iteration to look weird)
		straightsize = TrackGenerator.MAX_STRAIGHT if squaredistance <= (TrackGenerator.MAX_STRAIGHT*1.2)**2 else TrackGenerator.MAX_STRAIGHT/2
		(generated, curpoint,deltalength) = generate_straight(points[-1],straightsize,calculate_tangent_angle(points))
		length += deltalength
		points.extend(generated)
		#We'll either do a random cturn or a random hairpin, then continue the journey
		cturn_or_hairpin = uniform(0,1)
		makecturn = cturn_or_hairpin < 0.9
		if makecturn or (hairpined and not manyhairpins):#cturn
			(generated, curpoint,deltalength,output_normal) = generate_constant_turn(curpoint,
											uniform(TrackGenerator.MIN_CONSTANT_TURN,TrackGenerator.MAX_CONSTANT_TURN),
											calculate_tangent_angle(points),
											circlepercent=uniform(0,0.25),turnagainstnormal = output_normal)
			length += deltalength
			points.extend(generated)
			(generated, curpoint,deltalength,output_normal) = generate_constant_turn(curpoint,
											uniform(TrackGenerator.MIN_CONSTANT_TURN,TrackGenerator.MAX_CONSTANT_TURN),
											calculate_tangent_angle(points),
											circlepercent=uniform(0,0.25),turnagainstnormal = output_normal)
			length += deltalength
			points.extend(generated)
		else:
			#We only want an even amount of turns so that we can leave heading the same direction we entered.
			#otherwise due to the way we head towards the path, its basically guaranteed we get a self-intersection.
			numswitches = 2*randrange(TrackGenerator.MIN_HAIRPIN_NUM,TrackGenerator.MAX_HAIRPIN_NUM)
			(generated, curpoint,deltalength) = generate_hairpin_turn(curpoint,uniform(TrackGenerator.MIN_HAIRPIN,TrackGenerator.MAX_HAIRPIN),
										calculate_tangent_angle(points),switchbacknum=numswitches)
			length += deltalength
			points.extend(generated)
		#Now we recurse!
		if depth>0:
			(generated, curpoint, length) = generate_path_from_point_to_point(curpoint,endpoint,calculate_tangent_angle(points),depth-1,
											hairpined=hairpined or not makecturn,manyhairpins=manyhairpins,
											fuzzradius=fuzzradius)
			length += deltalength
			points.extend(generated)
		


	return (points,points[-1],length)

def generate_hairpin_turn(startpoint,radius,intangent,switchbacknum=None,turnleft=None,wobbliness=None,straightsize=None,circlesize=None,uniformcircles=True):
	curpoint = startpoint
	curtangent = intangent
	length = 0
	startleftnum = 0 if turnleft else 1

	#A hairpin has a few choices:
	#	How many switchbacks
	#	Direction of first switchback
	#	"Wobbliness" (circlepercent)
	#	Size of straightways
	turnleft = uniform(0,1)<0.5 									if turnleft == None 		else turnleft
	switchbacknum = 2*randrange(TrackGenerator.MIN_HAIRPIN_NUM,TrackGenerator.MAX_HAIRPIN_NUM)	if switchbacknum == None	else switchbacknum
	wobbliness = uniform(0.45,0.55)									if wobbliness == None		else wobbliness
	straightsize = uniform(TrackGenerator.MIN_STRAIGHT,TrackGenerator.MAX_STRAIGHT)			if straightsize == None		else straightsize
	circlesize = uniform(TrackGenerator.MIN_CONSTANT_TURN,TrackGenerator.MAX_CONSTANT_TURN)		if circlesize == None		else circlesize

	#We are interested in making sure switchbacks never intersect
	#If you draw a diagram, this gives you a diamond with angles pi/2,pi/2,L, and pi/2-L where L is:
	#((2*pi*(1-wobbliness))/2)
	#Using trigonometry, we can calculate the radius to intersection in terms of the angle and circle radius:
	#intersect_point = radius * tan(L)
	#If intersect_point is greater than max_intersection, we're good!
	#Otherwise we want to cap it there.  So we find the inverse-function for "wobbliness"
	#1-atan2(intersect_point,radius)/math.pi = wobbliness
	max_intersection = 50
	angle_l = (2*math.pi*(1-wobbliness))/2
	intersect_point = radius * math.tan(angle_l)
	#print("Point of intersection: "  + str(intersect_point))
	if intersect_point > max_intersection:
		#print("Capping wobbliness prevent intersection!")
		wobbliness = 1-math.atan2(max_intersection,radius)/math.pi
		#print("New wobbliness: " + str(wobbliness))

	points = []
	lastnormal = None
	for a in range(0,switchbacknum):
		#Switchback starts with a circle, then a line
		#then we repeat
	
		circlesize = circlesize if uniformcircles else uniform(TrackGenerator.MIN_CONSTANT_TURN,TrackGenerator.MAX_CONSTANT_TURN)

		#cturn
		(generated, curpoint,deltalength,lastnormal) = generate_constant_turn(curpoint,circlesize,curtangent,
										circlepercent=wobbliness,
										turnagainstnormal=lastnormal)
		length += deltalength
		points.extend(generated)
		curtangent = calculate_tangent_angle(points)

		#straight
		(generated, curpoint,deltalength) = generate_straight(curpoint,straightsize,curtangent)
		length += deltalength
		points.extend(generated)
		curtangent = calculate_tangent_angle(points)


	#Returns a list of points and the new edge of the racetrack and the change in length
	return (points,points[-1],length)


def generate_constant_turn_until_facing_point(startpoint,radius,intangent,goalpoint,normal,turnagainstnormal=False):
	#This is a split-off version of generate_constant_turn, where instead of taking in a percent to turn around a circle,
	#We give it a direction we want it to stop at


	#Calculate some preliminary information
	s = startpoint
	r = radius
	n = normal if turnagainstnormal else (-normal[0],-normal[1])
	n = normalize_vec(n)
	g = goalpoint
	c = (s[0]+r*n[0],s[1]+r*n[1])
	cg = (c[0]-g[0],c[1]-g[1])
	gc = (-cg[0],-cg[1])
	sc = (s[0]-c[0],s[1]-c[1])
	t = (math.cos(intangent),math.sin(intangent))
	x = magnitude( gc )
	if abs(r/x) > 1:
		return generate_constant_turn_until_facing_point(startpoint,x,intangent,goalpoint,normal,turnagainstnormal)


	#Figure out what quadrant we will have to depart the circle at (see team wiki for diagram)
	basis_changer = np.matrix( [ [t[0],n[0]],[t[1],n[1]] ] )

	old_g = np.matrix( [[gc[0]],[gc[1]]] )
	g_prime = np.matmul(basis_changer,old_g)
	quadrant = 1
	if (g_prime[0] >= 0 and -r <= g_prime[1] and g_prime[1] <= 0) or (g_prime[0] >= r and -r <= g_prime[1]):
		quadrant = 1
	elif (g_prime[1] >= 0 and 0 <= g_prime[0] and g_prime[0] <= r) or (g_prime[1] >= r and g_prime[0] <= r):
		quadrant = 2
	elif (g_prime[0] <= 0 and 0 <= g_prime[1] and g_prime[1] <= r) or (g_prime[0] <= -r and g_prime[1] <= r):
		quadrant = 3
	else:
		quadrant = 4

	
	#For each quadrant, we need to move what is considered the "start point"
	#By 90 degrees (see Track Generation guide on team wiki for reasoning)
	quadrant_angle = (quadrant-1) * math.pi/2
	quadrant_rotater = np.matrix( [ [math.cos(quadrant_angle),-math.sin(quadrant_angle)],[math.sin(quadrant_angle),math.cos(quadrant_angle)] ] )
	old_s = None
	swap_factor = -1 if turnagainstnormal else 1
	if quadrant == 1:
		old_s = np.matrix( [[sc[0]],[sc[1]]] )
	elif quadrant == 2:
		old_s = np.matrix( [[sc[0]],[swap_factor*sc[1]]] )
	elif quadrant == 3:
		old_s = np.matrix( [[sc[0]],[sc[1]]] )
	else:
		old_s = np.matrix( [[sc[0]],[swap_factor*sc[1]]] )
	new_s = np.matmul(quadrant_rotater,old_s)


	#Finally, voila
	dot = gc[0]*new_s[0] + gc[1]*new_s[1]
	first_acos = math.acos(r/x)
	second_acos = math.acos(dot/(x*r))


	theta = second_acos-first_acos + quadrant_angle

	cp = theta/(math.pi*2)

	toReturn = generate_constant_turn(startpoint,radius,intangent,circlepercent = cp,turnagainstnormal = turnagainstnormal)
	return toReturn


def get_parametric_circle(start_angle,end_angle,center_point,radius):
	#We can calculate points on a circle using a rotation matrix
	def output(sa,ea,cp,r,t):
		def lerp_angle(s,e,t_):
			return (e-s)*t_+s
		a       = lerp_angle(sa,ea,t)
		rot_mat = np.matrix( [ [math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)] ] )
		to_rot  = [[r],[0]]
		direc   = np.matmul( rot_mat,to_rot)
		return (cp[0]-direc.item(0),cp[1]+direc.item(1))
	return lambda t: output(start_angle,end_angle,center_point,radius,t)

def generate_constant_turn(startpoint,radius,intangent,circlepercent=None,turnagainstnormal=None):
	turnagainstnormal = uniform(0,1)<0.5 		if turnagainstnormal == None 		else turnagainstnormal
	circlepercent     = uniform(0.1,0.2)		if circlepercent == None 		else circlepercent


	tangent_vec = (math.cos(intangent), math.sin(intangent))
	normal_vec  = (-math.sin(intangent),math.cos(intangent))
	if turnagainstnormal: 
		normal_vec = (-normal_vec[0],-normal_vec[1])
	center = (startpoint[0]+normal_vec[0]*radius,startpoint[1]+normal_vec[1]*radius)
	shifted_start = (startpoint[0]-center[0],startpoint[1]-center[1])
	start_angle = math.atan2( shifted_start[1],shifted_start[0]-1 )
	end_angle   = start_angle + circlepercent*math.pi*2


	circle_function = get_parametric_circle(start_angle,end_angle,center,radius)

	fidelity = 100.0
	points = [circle_function((t if turnagainstnormal else -t)/fidelity) for t in range(0,int(fidelity)+1)]

	#Length of circle is, fortunately, easy!  It's simply radius*angle
	length = circlepercent*math.pi*2*radius

	#Now we want to find the normal vector, because it's useful to have to determine whether it curves inwards or outwards
	#Normal vectors are always parallel to the vector from center to end point
	normal = (points[-1][0]-center[0],points[-1][1]-center[1])

	#Returns a list of points and the new edge of the racetrack and the change in length
	return (points,points[-1],length,normal)
	

def generate_straight(startpoint,length,angle):
	(startx,starty) = startpoint

	#Now create a parameterized function in terms of the angle
	#This is easy - tan(angle) = slope, so y = mt + starty, x = t + startx
	#The length of this line is delx^2+dely^2 = length^2, so (mt)^2+t^2 = length^2
	#implying t^2 = length^2/(1+m^2)
	#So t ranges from 0 to length/sqrt(1+m^2)
	slope = math.tan(angle)
	tmax = length/math.sqrt(1+slope*slope)

	if angle*slope < 0:
		#I don't actually know the geometrical reason why this is needed :/
		#But if you don't do this, sometimes the line points the wrong way!
		tmax *=-1

	#Since we draw the track by placing lines, we only need the endpoints of this!
	#(For other curves we approximate by a bunch of small lines, so we'd need full data)
	#However we actually don't want that because it will mess with the self-intersection-detection
	#later on.
	scalefactor = 10.0
	if tmax >= 0:
		points = [(t/scalefactor+startx,slope*t/scalefactor+starty) for t in range(0,int(scalefactor*math.ceil(tmax)))]
	else:
		points = [(-t/scalefactor+startx,-slope*t/scalefactor+starty) for t in range(0,int(scalefactor*math.ceil(-tmax)))]
	#points = [startpoint,(tmax+startx,slope*tmax+starty)]


	#Returns a list of points and the new edge of the racetrack and the change in length
	return (points,points[-1],length)


def convert_points_to_all_positive(xys):
	#If the track dips to the negative side of the x or y axes, shift everything over
	#Returns shifted points tupled with the range over which the points span
	#We also want everything converted to an integer!
	maxnegx = 0
	maxnegy = 0
	maxx    = 0
	maxy    = 0

	for point in xys:
		(x,y) = point
		maxnegx = min(x,maxnegx)
		maxnegy = min(y,maxnegy)
		maxx    = max(x,maxx)
		maxy    = max(y,maxy)

	newxys = []
	padding = 10
	for point in xys:
		(x,y) = point
		newxys.append(((x-maxnegx)+padding,(y-maxnegy)+padding))

	return (newxys,int(maxx-maxnegx)+2*padding,int(maxy-maxnegy)+2*padding)


def compactify_points(points):
	#Given a list of int points, if any two adjacent points are the same then remove one of them
	removelist = []
	prevpoint = (-10000,-10000)
	def makint(tup):
		return (int(tup[0]),int(tup[1]))
	for a in range(0,len(points)):
		if (makint(points[a]) == makint(prevpoint)):
			removelist.append(a)
		prevpoint = points[a]
	for index in sorted(removelist,reverse=True):
		del points[index]
	return points

def check_if_overlap(points):
	#Naive check to see if track overlaps itself
	#(Won't catch overlaps due to track width, only if track center overlaps)
	points = points[:-10] #remove end points as in theory that should also be the start point
	#(I remove extra to be a little generous to it as a courtesy - I don't really care how well the
	#start loops to the end yet)

	#Now we want to fill in the diagonally-connected points, otherwise you can imagine
	#that two tracks moving diagonally opposite could cross eachother inbetween the pixels,
	#fooling our test.
	for index in range(1,len(points)):
		(sx,sy) = points[index-1]
		(ex,ey) = points[index]
		manhatdist = abs(ex-sx)+abs(ey-sy)
		if (manhatdist > 1):
			#moved diagonally, insert an extra point for it at the end!
			points.append( (sx+1,sy) if ex > sx else (sx-1,sy) )

	return len(set(points)) != len(points)



