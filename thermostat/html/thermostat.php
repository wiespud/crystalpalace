<!DOCTYPE html>

<html>
<meta http-equiv="refresh" content="10">
<body style="font-family:arial;font-weight:normal;color:silver;background-color:black;zoom:150%;">
<!-- <h1>The Crystal Palace</h1> -->
<h2>Thermostat</h2>
<h3>Status:&nbsp<?php include('curstat.txt'); ?></h3>
<!-- <h4>Hallway:&nbsp<?php include('hallwaytemp.txt'); ?>&nbsp&nbsp&nbsp&nbsp<?php include('hallwayhum.txt'); ?></h4> -->
<h4>Bedroom:&nbsp<?php include('bedroomtemp.txt'); ?></h4>
<h4>Nursery:&nbsp<?php include('nurserytemp.txt'); ?></h4>
<h4>Family&nbsproom:&nbsp<?php include('familyroomtemp.txt'); ?></h4>
<h4>Basement:&nbsp<?php include('basementtemp.txt'); ?></h4>
<h4>Closet:&nbsp<?php include('closettemp.txt'); ?></h4>
<h4></h4>
<h3>Settings</h3>
<h4>Temperature: <?php include('temp.txt'); ?> F</h4>
<a href='down.php'><button style='background-color:silver'>Down</button></a>&nbsp<a href='up.php'><button style='background-color:silver'>Up</button></a>
<h4>Mode: <?php include('mode.txt'); ?></h4>
<a href='cool.php'><button style='background-color:<?php include('cool_color.txt'); ?>'>Cool</button></a>&nbsp<a href='heat.php'><button style='background-color:<?php include('heat_color.txt'); ?>'>Heat</button></a>&nbsp<a href='off.php'><button style='background-color:silver'>Off</button></a>
<h4>Fan: <?php include('fan.txt'); ?></h4>
<a href='auto.php'><button style='background-color:<?php include('auto_color.txt'); ?>'>Auto</button></a>&nbsp<a href='on.php'><button style='background-color:<?php include('on_color.txt'); ?>'>On</button></a>
</body>
</html>
