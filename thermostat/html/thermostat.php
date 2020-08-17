<!DOCTYPE html>

<html>
    <script src='jquery-3.5.1.min.js'></script>
    <head>
        <meta http-equiv='Content-Type' content='text/html; charset=utf8' />
        <script type='text/javascript'>

            function refresh() {
                // handle updateme class elements
                var elems = document.getElementsByClassName('updateme');
                for (var i = 0; i < elems.length; i++) {
                    let req = new XMLHttpRequest();
                    let elem = elems[i];
                    let txtfile = 'thermostat_files/' + elem.getAttribute('txtfile');
                    req.onreadystatechange = function () {
                        if (req.readyState == 4 && req.status == 200) {
                            elem.innerText = req.responseText;
                        }
                    }
                    req.open('GET', txtfile, true);
                    req.setRequestHeader('Cache-Control', 'no-cache');
                    req.send(null);
                }
                // turn things red if last update was too long ago
                var thermostat = document.getElementById('thermostat');
                var lastupdate = document.getElementById('lastupdate');
                var lastupdateval = document.getElementById('lastupdateval');
                var date = new Date();
                var now = date.getTime();
                var ts = Date.parse(lastupdateval.innerText);
                if (now > ts + 60000.0) {
                    thermostat.style.color = 'red';
                    lastupdate.style.color = 'red';
                } else {
                    thermostat.style.color = 'silver';
                    lastupdate.style.color = 'silver';
                }
            }

            function init() {
                refresh();
                var int = self.setInterval(function () {
                    refresh();
                }, 5000);
            }

            function button(elem) {
                if (elem.hasAttribute('settext')) {
                    var settext_name = elem.getAttribute('settext');
                    var settext_elem = document.getElementById(settext_name);
                    settext_elem.innerText = elem.id;
                }
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
                if (elem.hasAttribute('decrement')) {
                    var decrement_name = elem.getAttribute('decrement');
                    var decrement_elem = document.getElementById(decrement_name);
                    var number = decrement_elem.innerText;
                    number--;
                    decrement_elem.innerText = number;
                }
                if (elem.hasAttribute('increment')) {
                    var increment_name = elem.getAttribute('increment');
                    var increment_elem = document.getElementById(increment_name);
                    var number = increment_elem.innerText;
                    number++;
                    increment_elem.innerText = number;
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

<h2 id='thermostat'>Thermostat</h2>

<h3>Status: <a class='updateme' txtfile='curstat.txt'></a> <a class='updateme' txtfile='averagetemp.txt'></a></h3>
<h4>Bedroom: <a class='updateme' txtfile='bedroomtemp.txt'></a></h4>
<h4>Nursery: <a class='updateme' txtfile='nurserytemp.txt'></a></h4>
<h4>Family room: <a class='updateme' txtfile='familyroomtemp.txt'></a></h4>
<h4>Basement: <a class='updateme' txtfile='basementtemp.txt'></a></h4>
<h4>Closet: <a class='updateme' txtfile='closettemp.txt'></a></h4>

<h3>Settings</h3>
<h4>Temperature: <a class='updateme' id='temp' txtfile='temp.txt'></a></h4>
<button class='temp' id='Down' onclick='button(this)' decrement='temp' style='background-color:silver'>Down</button>
<button class='temp' id='Up' onclick='button(this)' increment='temp' style='background-color:silver'>Up</button>
<h4>Mode: <a class='updateme' id='mode' txtfile='mode.txt'></a></h4>
<button class='mode' id='Cool' onclick='button(this)' settext='mode' colorme='aqua' uncolor='Heat' style='background-color:<?php include('thermostat_files/cool_color.txt'); ?>'>Cool</button>
<button class='mode' id='Heat' onclick='button(this)' settext='mode' colorme='orange' uncolor='Cool' style='background-color:<?php include('thermostat_files/heat_color.txt'); ?>'>Heat</button>
<button class='mode' id='Off' onclick='button(this)' settext='mode' uncolor='Heat,Cool' style='background-color:silver'>Off</button>
<h4>Fan: <a class='updateme' id='fan' txtfile='fan.txt'></a></h4>
<button class='fan' id='Auto' onclick='button(this)' settext='fan' colorme='lime' uncolor='On' style='background-color:<?php include('thermostat_files/auto_color.txt'); ?>'>Auto</button>
<button class='fan' id='On' onclick='button(this)' settext='fan' colorme='lime' uncolor='Auto' style='background-color:<?php include('thermostat_files/on_color.txt'); ?>'>On</button>

<h3>Statistics</h3>
<h4>Duty Cycle: <a class='updateme' txtfile='hourdutycycle.txt'></a> (hour) <a class='updateme' txtfile='daydutycycle.txt'></a> (day)</h4>
<h4 id='lastupdate'>Last Update: <a class='updateme' id='lastupdateval' txtfile='lastupdate.txt'></a></h4>

</body>
</html>
