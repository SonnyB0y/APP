const API_BASE_URL = "http://localhost:8000";

// Hjelpefunktion til at læse ?token=xyz fra browserens URL
function getEventTokenFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("token");
}

// 1. HENT AFTALE (GET /events/{public_token})
async function loadEventFromBackend() {
    const token = getEventTokenFromUrl();
    if (!token) {
        console.log("Ingen token i URL - viser 'Opret ny aftale' eller demo-visning.");
        return;
    }

    // Hvis brugeren har forbundet sin kalender, ligger tokenet i sessionStorage
    const calendarToken = sessionStorage.getItem("google_access_token");
    const headers = { "Content-Type": "application/json" };
    if (calendarToken) {
        headers["x-calendar-token"] = calendarToken;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/events/${token}`, { headers });
        if (!response.ok) throw new Error("Aftalen blev ikke fundet i databasen");
        
        const eventData = await response.json();
        
        // Opdater UI med rigtige data fra PostgreSQL
        renderEventToUI(eventData);
    } catch (error) {
        alert("Fejl ved hentning af aftale: " + error.message);
    }
}

// 2. OPRET NY AFTALE (POST /events/)
async function createNewEvent(title, description, timeOptionsArray) {
    // timeOptionsArray skal være: [{ start_time: "2026-10-22T10:00:00Z", end_time: "2026-10-22T11:00:00Z" }, ...]
    const payload = {
        title: title,
        description: description,
        time_options: timeOptionsArray
    };

    try {
        const response = await fetch(`${API_BASE_URL}/events/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("Kunne ikke oprette aftalen");

        const createdEvent = await response.json();
        
        // Send brugeren direkte videre til den nyoprettede afstemning via dens unikke public_token
        window.location.search = `?token=${createdEvent.public_token}`;
    } catch (error) {
        alert("Fejl ved oprettelse: " + error.message);
    }
}

// 3. INDSEND STEMMER (POST /events/{public_token}/vote)
async function submitParticipantVotes(participantName, selectedVotesArray) {
    // selectedVotesArray skal være: [{ time_option_id: 1, status: "yes" }, { time_option_id: 2, status: "if_need_be" }]
    const token = getEventTokenFromUrl();
    if (!token) {
        alert("Du er i demo-tilstand. Opret en rigtig aftale først for at gemme i databasen!");
        return;
    }

    const payload = {
        participant_name: participantName,
        votes: selectedVotesArray
    };

    try {
        const response = await fetch(`${API_BASE_URL}/events/${token}/vote`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("Kunne ikke gemme dine stemmer");

        // Genindlæs aftalen fra databasen så tabellen opdateres med det samme
        await loadEventFromBackend();
    } catch (error) {
        alert("Fejl ved afstemning: " + error.message);
    }
}

// Kør automatisk når siden åbnes
document.addEventListener("DOMContentLoaded", () => {
    loadEventFromBackend();
});