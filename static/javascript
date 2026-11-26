// Campus Connect - small standalone console for the Flask API.
const STATS_URL = "/api/stats";

function getJson(url) {
  return fetch(url).then(function (response) {
    if (!response.ok) throw new Error("Request failed: " + response.status);
    return response.json();
  });
}

function label(key) {
  return String(key).replace(/_/g, " ").replace(/\b\w/g, function (letter) {
    return letter.toUpperCase();
  });
}

function cell(value) {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function renderRows(rows) {
  const body = document.getElementById("data-table");
  if (!body) return;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="8" class="muted">No records yet.</td></tr>';
    return;
  }
  const keys = Object.keys(rows[0]);
  body.innerHTML = rows
    .map(function (row) {
      return (
        "<tr>" +
        keys
          .map(function (key) {
            return "<td>" + cell(row[key]) + "</td>";
          })
          .join("") +
        "</tr>"
      );
    })
    .join("");
}

function loadPage() {
  const page = document.body.dataset.page;

  if (page === "dashboard") {
    getJson(STATS_URL)
      .then(function (stats) {
        document.querySelectorAll("[data-stat]").forEach(function (node) {
          node.textContent = stats[node.dataset.stat] || 0;
        });
      })
      .catch(function (error) {
        console.error(error);
      });
    return;
  }

  const endpoints = {
    students: "/api/students",
    courses: "/api/courses",
    enrollment: "/api/enrollments",
    announcements: "/api/announcements",
  };

  getJson(endpoints[page] || "/api/students")
    .then(renderRows)
    .catch(function (error) {
      const body = document.getElementById("data-table");
      if (body) body.innerHTML = '<tr><td colspan="8" class="muted">' + error.message + "</td></tr>";
    });
}

document.addEventListener("DOMContentLoaded", loadPage);

