<?php
$arg = $_POST['arg'];
exec('/home/pi/thermostat.py '.$arg);
?>
