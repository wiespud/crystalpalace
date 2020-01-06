<?php
exec('/home/pi/thermostat.py mode Heat');
header('Location: thermostat.php');
?>
