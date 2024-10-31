// ---- ASYNC AJAX for autocompletion --------------------------------
document.getElementById("new_exercise").addEventListener("input", function() {
    let query = this.value;
    if (query.length > 0) {
        let xhr = new XMLHttpRequest();
        xhr.open("GET", "/create_workout?query=" + query, true);  // Use /create_workout route for AJAX
        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4 && xhr.status == 200) {
                let response = JSON.parse(xhr.responseText);
                let suggestions = document.getElementById("exercise_suggestions");
                suggestions.innerHTML = "";  // Clear previous suggestions
                if (response.length > 0) {
                    suggestions.style.display = "block";  // Show the suggestion list
                    response.forEach(function(exercise) {
                    let li = document.createElement("li");
                    li.classList.add("dropdown-item");  // Add this line to apply Bootstrap hover effect
                    li.textContent = exercise;
                    li.onclick = function() {
                        document.getElementById("new_exercise").value = exercise;
                        suggestions.style.display = "none";  // Hide the suggestion list
                    };
                    suggestions.appendChild(li);
                });
                } else {
                    suggestions.style.display = "none";  // Hide if no matches
                }
            }
        };
        xhr.send();
    } else {
        document.getElementById("exercise_suggestions").style.display = "none";  // Hide suggestions if input is empty
    }
});
