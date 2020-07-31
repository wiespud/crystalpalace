<!DOCTYPE html>

<html>
    <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf8" />
        <script type="text/javascript">

            function refresh() {
                var elems = document.getElementsByClassName('updateme');
                for (var i = 0; i < elems.length; i++) {
                    let req = new XMLHttpRequest();
                    let elem = elems[i];
                    let prefix = elem.getAttribute('prefix');
                    let txtfile = 'thermostat_files/' + elem.getAttribute('txtfile');
                    req.onreadystatechange = function () {
                        if (req.readyState == 4 && req.status == 200) {
                            elem.innerText = prefix + req.responseText;
                        }
                    }
                    req.open('GET', txtfile, true);
                    req.setRequestHeader('Cache-Control', 'no-cache');
                    req.send(null);
                }
            }

            function init() {
                refresh();
                var int = self.setInterval(function () {
                    refresh();
                }, 1000);
            }

            function button(elem) {
                if (elem.hasAttribute('uncolor')) {
                    var uncolor_names = elem.getAttribute('uncolor');
                    var uncolor_array = uncolor_names.split(',');
                    for (var i = 0; i < uncolor_array.length; i++) {
                        var uncolor_elem = document.getElementById(uncolor_array[i]);
                        uncolor_elem.style.backgroundColor = 'silver';
                    }
                }
                if (elem.hasAttribute('colorme')) {
                    var new_color = elem.getAttribute('colorme');
                    elem.style.backgroundColor = new_color;
                }
                var python_args = elem.className + ' ' + elem.id;
                $.ajax({
                    url: 'python.php',
                    type: 'post',
                    data: { 'arg': python_args }
                });
            }

        </script>
    </head>

<body onload='init()' style='font-family:arial;font-weight:normal;color:silver;background-color:black;zoom:190%;'>

<!-- <h1>The Crystal Palace</h1> -->

<h2>Thermostat</h2>

<h3>
    <a class='updateme' txtfile='curstat.txt' prefix='Status: '></a>
    <a class='updateme' txtfile='averagetemp.txt' prefix=' '></a>
</h3>
<h4 class='updateme' txtfile='bedroomtemp.txt' prefix='Bedroom: '></h4>
<h4 class='updateme' txtfile='nurserytemp.txt' prefix='Nursery: '></h4>
<h4 class='updateme' txtfile='familyroomtemp.txt' prefix='Family room: '></h4>
<h4 class='updateme' txtfile='basementtemp.txt' prefix='Basement: '></h4>
<h4 class='updateme' txtfile='closettemp.txt' prefix='Closet: '></h4>

<h3>Settings</h3>
<h4 class='updateme' txtfile='temp.txt' prefix='Temperature: '></h4>
<button class='temp' id='Down' onclick='button(this)' style='background-color:silver'>Down</button>
<button class='temp' id='Up' onclick='button(this)' style='background-color:silver'>Up</button>
<h4 class='updateme' txtfile='mode.txt' prefix='Mode: '></h4>
<button class='mode' id='Cool' onclick='button(this)' colorme='aqua' uncolor='Heat' style='background-color:<?php include('thermostat_files/cool_color.txt'); ?>'>Cool</button>
<button class='mode' id='Heat' onclick='button(this)' colorme='orange' uncolor='Cool' style='background-color:<?php include('thermostat_files/heat_color.txt'); ?>'>Heat</button>
<button class='mode' id='Off' onclick='button(this)' uncolor='Heat,Cool' style='background-color:silver'>Off</button>
<h4 class='updateme' txtfile='fan.txt' prefix='Fan: '></h4>
<button class='fan' id='Auto' onclick='button(this)' colorme='lime' uncolor='On' style='background-color:<?php include('thermostat_files/auto_color.txt'); ?>'>Auto</button>
<button class='fan' id='On' onclick='button(this)' colorme='lime' uncolor='Auto' style='background-color:<?php include('thermostat_files/on_color.txt'); ?>'>On</button>

<h3>Statistics</h3>
<h4>
    <a class='updateme' txtfile='hourdutycycle.txt' prefix='Duty Cycle: '></a>
    <a class='updateme' txtfile='daydutycycle.txt' prefix=' (hour) '></a>
    (day)
</h4>
<h4 class='updateme' txtfile='lastupdate.txt' prefix='Last Update: '></h4>

</body>
</html>
