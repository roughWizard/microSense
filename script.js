google.charts.load('current', { 'packages': ['corechart'] });
google.charts.setOnLoadCallback(initializeCharts);

let accelData, accelChart, tempData, tempChart;
let accelDataTable = [['Time', 'Accelerometer X']];
let tempDataTable = [['Time', 'Temperature']];
let timeIndex = 0;

let port;
let writer;  // Declare writer here
let keepReading = true;
let readBuffer = ""; // Buffer to accumulate incomplete messages

let sensorConfigured = false;  // Track whether the sensor is configured

function initializeCharts() {
    // Accelerometer X Chart
    accelChart = new google.visualization.LineChart(document.getElementById('accelChart'));

    // Temperature Chart
    tempChart = new google.visualization.LineChart(document.getElementById('tempChart'));
}

function updateCharts(accelX, temp) {
    timeIndex++;

    // Update Accelerometer X chart
    accelDataTable.push([timeIndex, accelX]);
    if (accelDataTable.length > 50) accelDataTable.splice(1, 1); // Keep only last 50 points
    accelData = google.visualization.arrayToDataTable(accelDataTable);
    accelChart.draw(accelData, { title: `Accelerometer X (latest : ${accelX.toFixed(2)})`, curveType: 'none', legend: 'none', vAxis: { title: 'milli-g' } });

    // Update Temperature chart
    tempDataTable.push([timeIndex, temp]);
    if (tempDataTable.length > 50) tempDataTable.splice(1, 1);
    tempData = google.visualization.arrayToDataTable(tempDataTable);
    tempChart.draw(tempData, { title: `Temperature (latest : ${temp.toFixed(2)})`, curveType: 'none', legend: 'none', vAxis: { title: '°C' } });
}

async function connectMicrobit() {
    try {
        // Request USB device and open connection
        port = await navigator.serial.requestPort();
        await port.open({ baudRate: 115200 });
        console.log("Connected to Micro:bit");
        document.getElementById('connectionStatus').textContent = "Connected";
        document.getElementById('sensorConfiguration').style.display = "block";
        document.getElementById('connectButton').style.display = "none";  // Hide connect button

        // Get the writer when connected
        writer = port.writable.getWriter();
        readData();  // Start reading data from Micro:bit
    } catch (error) {
        console.error("Error connecting to Micro:bit:", error);
    }
}

async function readData() {
    while (port.readable && keepReading) {
        try {
            const reader = port.readable.getReader();
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                if (value) {
                    const text = new TextDecoder().decode(value);
                    readBuffer += text;

                    // Process complete lines
                    let lines = readBuffer.split('\n');
                    readBuffer = lines.pop();
                    for (let line of lines) {
                        handleIncomingData(line.trim());
                    }
                }
            }
            reader.releaseLock();
        } catch (error) {
            console.error("Error reading data:", error);
        }
    }
}

function handleIncomingData(data) {
  console.log("handling incoming data:",data)
    const dataParts = data.split(',');
    const sensorData = {};
    dataParts.forEach(part => {
        const [key, value] = part.split(':');
        if (key === 'accel_x') {
            const accelValue = parseFloat(value);
            if (!isNaN(accelValue)) sensorData[key] = accelValue;
        } else if (key === 'temp') {
            const tempValue = parseFloat(value);
            if (!isNaN(tempValue)) sensorData[key] = tempValue;
        }
    });

    if (sensorData.accel_x !== undefined && sensorData.temp !== undefined) {
        console.log("Valid data received:", sensorData);
        updateCharts(sensorData.accel_x, sensorData.temp);
    }
}

function sendSensorConfig() {
    if (!writer) {
        console.error("Writer not available. Please connect the Micro:bit first.");
        return;
    }

    const sensorType = document.getElementById('sensorType').value;
    const sensorChannel = parseInt(document.getElementById('sensorChannel').value);

    const sensorConfig = {
        type: sensorType,
        channel: sensorChannel
    };

    // Create a command string to send
    const command = `SET_SENSOR:${JSON.stringify(sensorConfig)}\n`;

    // Send the command using the writer
    writer.write(new TextEncoder().encode(command));
    console.log("Sensor configuration sent:", sensorConfig);

    sensorConfigured = true;
    document.getElementById('recordDataSection').style.display = "block"; // Show "Record Data" button
}

async function recordData() {
    if (sensorConfigured) {
        const command = "SEND_DATA\n";
        await writer.write(new TextEncoder().encode(command));  // Send data command using writer
        console.log("Send data command sent");
    }
}

document.getElementById('connectButton').addEventListener('click', connectMicrobit);
document.getElementById('sendSensorConfigButton').addEventListener('click', sendSensorConfig);
document.getElementById('recordDataButton').addEventListener('click', recordData);
