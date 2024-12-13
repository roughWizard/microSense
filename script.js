google.charts.load('current', { 'packages': ['corechart'] });

let port;
let writer;
let reader;
let keepReading = true;
let readBuffer = "";
let sensorData = [];
let timeIndex = 0;
let selectedSensor = '';
let sensorType = 'none';
let sensorChannel = '0';
let chart;
let dataTable;

document.getElementById('connectButton').addEventListener('click', connectMicrobit);
document.getElementById('recordDataButton').addEventListener('click', startRecording);
document.getElementById('stopRecordingButton').addEventListener('click', stopRecording);
document.getElementById('downloadDataButton').addEventListener('click', downloadData);
document.getElementById('sensorDropdown').addEventListener('change', updateSensor);
document.getElementById('sensorTypeDropdown').addEventListener('change', updateSensorType);
document.getElementById('sensorChannelDropdown').addEventListener('change', updateSensorChannel);

async function connectMicrobit() {
    try {
        const selectedPort = await navigator.serial.requestPort();
        port = selectedPort;
        await port.open({ baudRate: 115200 });

        // Create writer for sending data
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
    while (port.readable && keepReading) {
        try {
            const { value, done } = await reader.read();
            if (done) break;
            if (value) {
                const text = new TextDecoder().decode(value);
                readBuffer += text;

                let lines = readBuffer.split('\n');
                readBuffer = lines.pop();

                for (let line of lines) {
                    // Log incoming data before processing
                    console.log("Received data:", line.trim());
                    handleIncomingData(line.trim());
                }
            }
        } catch (error) {
            console.error("Error reading data:", error);
        }
    }
}

function handleIncomingData(data) {
    if (data.startsWith('sensor_value:')) {
        const sensorValue = parseFloat(data.split(':')[1]);

        if (!isNaN(sensorValue)) {
            timeIndex++;
            const timestamp = (timeIndex / 10).toFixed(1); // Simulate timestamp in seconds with 0.1s accuracy
            sensorData.push([timestamp, sensorValue]);

            // Update chart data
            dataTable.addRow([timestamp, sensorValue]);
            chart.draw(dataTable, {
                title: selectedSensor + ' Data',
                curveType: 'none',
                legend: { position: 'none' },
                vAxis: { title: 'Value' }
            });
        }
    }
}


function updateSensorType() {
    sensorType = document.getElementById('sensorTypeDropdown').value;
    if (sensorType === 'analog' && selectedSensor === 'photoresistor') {
        sensorChannel = '0';
    } else if (sensorType === 'internal' && selectedSensor === 'accelX') {
        sensorChannel = 'none';
    }
    document.getElementById('sensorChannelDropdown').value = sensorChannel;
}

function updateSensorChannel() {
    sensorChannel = document.getElementById('sensorChannelDropdown').value;
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

function updateSensor() {
    const selectedSensor = document.getElementById('sensorDropdown').value;

    let localSensorType, localSensorChannel;

    if (selectedSensor === 'photoresistor') {
        localSensorType = 'analog';
        localSensorChannel = '0';
    } else if (selectedSensor === 'accelX') {
        localSensorType = 'internal';
        localSensorChannel = 'none';
    } else {
        localSensorType = 'none';
        localSensorChannel = 'none';
    }

    document.getElementById('sensorTypeDropdown').value = localSensorType;
    document.getElementById('sensorChannelDropdown').value = localSensorChannel;

    resetChart();
}


function stopRecording() {
    const command = 'STOP_DATA';
    writeData(command);  // Stop data recording command
    console.log("Data recording stopped.");

    document.getElementById('stopRecordingButton').disabled = true;
    document.getElementById('recordDataButton').disabled = false;
    // Don't disable the "Download Data" button when stopping the recording
}


function writeData(command) {
    // Log and send the data
    console.log("Sending data:", command);
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
