<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Beehive Monitor Dashboard</title>
  
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>

  <!-- jQuery & DataTables -->
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
  <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
  <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">

  <style>
    body { font-family: Arial, sans-serif; text-align: center; }
    .container { width: 90%; margin: auto; padding: 20px; }
    canvas { max-width: 100%; }
    button { padding: 10px; margin: 10px; }
    table { width: 100%; }
  </style>
</head>
<body>

  <h1>Beehive Monitor Dashboard</h1>

  <!-- Dropdowns & Date Inputs -->
  <div>
    <select id="macSelect"></select>
    <select id="measurementSelect"></select>
    <input type="date" id="startDate">
    <input type="date" id="endDate">
    <button onclick="loadChart()">Load Chart</button>
  </div>

  <!-- Chart -->
  <canvas id="myChart"></canvas>

  <!-- Data Table -->
  <h2>All Sensor Data</h2>
  <table id="dataTable">
    <thead>
      <tr><th>Timestamp</th><th>Device</th><th>Measurement</th><th>Value</th></tr>
    </thead>
    <tbody></tbody>
  </table>

  <script>
    let myChart;

    function loadDevices() {
      fetch("/api/devices").then(res => res.json()).then(data => {
        const select = document.getElementById("macSelect");
        select.innerHTML = data.map(mac => `<option value="${mac}">${mac}</option>`).join("");
      });
    }

    function loadMeasurements() {
      const mac = document.getElementById("macSelect").value;
      fetch(`/api/measurements/${mac}`).then(res => res.json()).then(data => {
        const select = document.getElementById("measurementSelect");
        select.innerHTML = data.map(m => `<option value="${m}">${m}</option>`).join("");
      });
    }

    function loadChart() {
      const mac = document.getElementById("macSelect").value;
      const measurement = document.getElementById("measurementSelect").value;
      const start = document.getElementById("startDate").value;
      const end = document.getElementById("endDate").value;

      fetch(`/api/history/${mac}/${measurement}?start=${start}&end=${end}`)
        .then(res => res.json())
        .then(data => {
          if (myChart) myChart.destroy();
          myChart = new Chart(document.getElementById("myChart"), {
            type: 'line',
            data: { labels: data.timestamps, datasets: [{ label: measurement, data: data.values }] }
          });
        });
    }

    $(document).ready(function() {
      $('#dataTable').DataTable({
        ajax: "/api/all_data",
        columns: [{ data: "timestamp" }, { data: "mac_address" }, { data: "measurement" }, { data: "value" }]
      });
    });

    loadDevices();
    document.getElementById("macSelect").addEventListener("change", loadMeasurements);
  </script>

</body>
</html>
