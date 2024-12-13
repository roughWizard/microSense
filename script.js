google.charts.load('current', { 'packages': ['corechart'] });

let port;
let writer;
let reader;
let readBuffer = "";
let sensorData = [];
let timeIndex = 0;
let selectedSensor = '';
let sensorType = 'none';
let sensorChannel = '0';
let chart;
let dataTable;


// Populate drop down menus for "select sensor" and "channel"
populateFields();
function populateFields() {
	// List of recognized sensors
	let sensors = [
		["Photoresistor", "photoresistor"],
		["Variable resistor", "variableResistor"],
		["Internal accelerometer X", "accelx"],
		["Internal temperature", "temp"]
	];

	sensors.forEach(sensor => {
		const option = document.createElement("option"); // Create a new <option> element
		option.text = sensor[0]; // Set the text of the option (the name)
		option.value = sensor[1]; // Set the value of the option (the value)
		document.getElementById("sensorTypeDropdown").appendChild(option); // Append the option to the dropdown
	});

	// Channels available
	const maxChannels = 1; // Starts at 0 and goes to maxChannels
	for (let i=0; i<=maxChannels; i++) {
		const option = document.createElement("option"); // Create a new <option> element
		option.text = i; // Set the text of the option (the name)
		option.value = i; // Set the value of the option (the value)
		document.getElementById("sensorChannelDropdown").appendChild(option); // Append the option to the dropdown		
	}
}

document.getElementById('connectButton').addEventListener('click', connectMicrobit);
document.getElementById('sensorTypeDropdown').addEventListener('change', resetChart);
document.getElementById('recordDataButton').addEventListener('click', startRecording);
document.getElementById('stopRecordingButton').addEventListener('click', stopRecording);
document.getElementById('downloadDataButton').addEventListener('click', downloadData);


async function connectMicrobit() {
  try {
	const selectedPort = await navigator.serial.requestPort();
	port = selectedPort;
	await port.open({ baudRate: 115200 });

	// Create writer for sending data and reader for receiving data
	writer = port.writable.getWriter();
	reader = port.readable.getReader();
	
	console.log("Micro:bit connected.");
	document.getElementById('recordDataButton').disabled = false;
	readData(); // Start reading data from the microbit
  } catch (error) {
		console.error("Error connecting to Micro:bit:", error);
  }
}

async function readData() {
  while (port && port.readable) {
		try {
		  const { value, done } = await reader.read();
		  if (done) break;
		  if (value) {
				const text = new TextDecoder().decode(value);
				readBuffer += text;

				let lines = readBuffer.split('\n'); // String to array on with /n delimiter (makes /n disappear too)
				readBuffer = lines.pop(); // Leftover after /n (if any)

				for (let line of lines) { // Process each command one at a time (if more than one)
				  // Log incoming data before processing
				  //console.log("Received data:", line.trim());
				  handleIncomingData(line.trim());
				}
		  }
		} catch (error) {
		  console.error("Error reading data:", error);
      break; // Exit on error to prevent infinite loop
		}
  }
  console.log("Reader closed or disconnected.");
}

function handleIncomingData(data) {
  if (data.startsWith('data:')) {
		const [time, sensorValue] = data.replace("data:","").split(","); // Remove identifier and make into array
		
		if (! (isNaN(time) && isNaN(sensorValue)) ) {
			time = (time / 1000).toFixed(1); // Convert ms to s and round to tenth
		  sensorData.push([time, sensorValue]);

		  // Update chart data
		  dataTable.addRow([time, sensorValue]);
			  chart.draw(dataTable, {
				title: selectedSensor + ' Data',
				curveType: 'none',
				legend: { position: 'none' },
				vAxis: { title: 'Value' }
		  });
		}
  }
}

function startRecording() {
  // Local variables for sensor type and channel
  let localSensorType = document.getElementById('sensorTypeDropdown').value;
  let localSensorChannel = document.getElementById('sensorChannelDropdown').value;

  sensorData = [];
  timeIndex = 0;
  resetChart();

  // Retrieve current settings for sensor type and channel
  console.log("Current sensor settings:", localSensorType, localSensorChannel);

  // Create the sensor configuration command
  let command = `SET_SENSOR:{"type":"${localSensorType}","channel":"${localSensorChannel}"}`;
  writeData(command);  // Send sensor configuration command

  // Start data recording command
  command = 'SEND_DATA';
  writeData(command);  // Send command to start recording data

  document.getElementById('stopRecordingButton').disabled = false;
  document.getElementById('recordDataButton').disabled = true;
  document.getElementById('downloadDataButton').disabled = false;  // Enable the "Download Data" button
}

function stopRecording() {
  const command = 'STOP_DATA';
  writeData(command,"Stopping data recording");  // Stop data recording command

  document.getElementById('stopRecordingButton').disabled = true;
  document.getElementById('recordDataButton').disabled = false;
  // Don't disable the "Download Data" button when stopping the recording
}

function writeData(command,logging="Sending data:") { // Default value for logging if none given
  // Log and send the data
  console.log(logging, ":", command);
  writer.write(new TextEncoder().encode(command + '\n'));  // Send data
}

function downloadData() {
  let sensorName = selectedSensor.charAt(0).toUpperCase() + selectedSensor.slice(1);
  let now = new Date();
  let timestamp = now.toISOString().replace('T', ' ').slice(0, 19);
  let filename = `${sensorName} ${timestamp}.csv`;

  let csvContent = "Time,Sensor Value\n";
  sensorData.forEach(row => {
	csvContent += `${row[0]},${row[1]}\n`;
  });

  let blob = new Blob([csvContent], { type: 'text/csv' });
  let link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}

function resetChart() {
  dataTable = new google.visualization.DataTable();
  dataTable.addColumn('string', 'Time');
  dataTable.addColumn('number', 'Sensor Value');

  chart = new google.visualization.LineChart(document.getElementById('chart_div'));
  chart.draw(dataTable, { title: 'Sensor Data', curveType: 'none', legend: { position: 'none' }, vAxis: { title: 'Value' } });
}
