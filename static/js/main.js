// Seed ERP Main Application JavaScript
document.addEventListener("DOMContentLoaded", function () {
    // Sidebar Toggle
    const toggleBtn = document.getElementById("menu-toggle");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", function (e) {
            e.preventDefault();
            document.getElementById("wrapper").classList.toggle("toggled");
        });
    }

    // Theme Switcher (Dark/Light)
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const currentTheme = document.documentElement.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
        });

        const savedTheme = localStorage.getItem("theme") || "light";
        document.documentElement.setAttribute("data-theme", savedTheme);
    }
});

// Global DataTables Configuration & Error Suppressor
if (window.jQuery && $.fn.dataTable) {
    // Suppress raw browser alert popups from DataTables
    $.fn.dataTable.ext.errMode = 'none';

    // Safe DataTables auto-initialization helper
    window.initSafeDataTable = function(selector, options) {
        var $el = $(selector);
        if ($el.length) {
            if (!$.fn.DataTable.isDataTable($el)) {
                var defaultOptions = {
                    retrieve: true,
                    pageLength: 15,
                    language: {
                        emptyTable: "No records found in database"
                    }
                };
                $.extend(defaultOptions, options || {});
                return $el.DataTable(defaultOptions);
            }
        }
    };
}
