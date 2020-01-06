<?php
exec('/home/pi/thermostat.py mode Cool');
header('Location: thermostat.php');
?>
