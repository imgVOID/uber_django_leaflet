// Interfaces for clarity
interface LocationData {
  lat: number;
  lng: number;
  accuracy: number;
  timestamp: number;
}

interface TaxiRequest {
  from: string;
  to: string;
  when: string;
}

interface NominatimResult {
  lat: string;
  lon: string;
  display_name: string;
}

// Helpers
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  return parts.length === 2 ? parts.pop()?.split(';').shift() || null : null;
}

// Wrap initialization in DOMContentLoaded to ensure elements exist
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('taxiForm') as HTMLFormElement | null;
  const status = document.getElementById('status') as HTMLElement | null;
  const last = document.getElementById('last') as HTMLElement | null;
  const fromAddr = document.getElementById('from_addr') as HTMLInputElement | null;
  const toAddr = document.getElementById('to_addr') as HTMLInputElement | null;

  if (!form || !status || !last || !fromAddr || !toAddr) return;

  // Initialization
  function showLast(): void {
    const data = localStorage.getItem('last_taxi_request');
    last!.textContent = data ? data : 'No requests yet.';
  }
  showLast();

  // Geocoding Handler
  async function verifyAddress(inputElement: HTMLInputElement, resultsContainerElement: HTMLElement): Promise<void> {
    const query = inputElement.value.trim();
    if (!query) {
      status!.textContent = 'Please enter an address to check.';
      return;
    }

    const coordRegex = /^-?\d+\.\d+,\s*-?\d+\.\d+$/;
    if (coordRegex.test(query)) {
      status!.textContent = 'Coordinates detected. No text search needed.';
      return;
    }

    status!.textContent = 'Searching OpenStreetMap...';
    resultsContainerElement.innerHTML = '';
    resultsContainerElement.classList.add('d-none');

    try {
      const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=5`;
      const response = await fetch(url, { headers: { 'Accept-Language': 'en' } });
      if (!response.ok) throw new Error('Network response code error');
      
      const data: NominatimResult[] = await response.json();
      
      if (data.length === 0) {
        status!.textContent = 'No matching address found on OpenStreetMap.';
        return;
      }

      status!.textContent = `Found ${data.length} matches. Choose one below.`;
      resultsContainerElement.classList.remove('d-none');

      data.forEach(item => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'list-group-item list-group-item-action small text-truncate';
        btn.textContent = item.display_name;
        
        btn.addEventListener('click', () => {
          inputElement.value = `${parseFloat(item.lat).toFixed(5)}, ${parseFloat(item.lon).toFixed(5)}`;
          resultsContainerElement.classList.add('d-none');
          resultsContainerElement.innerHTML = '';
          status!.textContent = 'Address verified and set to coordinates.';
        });
        resultsContainerElement.appendChild(btn);
      });
    } catch (err) {
      status!.textContent = 'Error connecting to OpenStreetMap API.';
    }
  }

  // Event Listeners
  document.getElementById('checkFromBtn')?.addEventListener('click', () => 
    verifyAddress(fromAddr, document.getElementById('fromResults')!)
  );

  document.getElementById('checkToBtn')?.addEventListener('click', () => 
    verifyAddress(toAddr, document.getElementById('toResults')!)
  );

  // Close dropdowns
  document.addEventListener('click', (e: Event) => {
    if (!(e.target as HTMLElement).closest('.position-relative-container')) {
      document.getElementById('fromResults')?.classList.add('d-none');
      document.getElementById('toResults')?.classList.add('d-none');
    }
  });

  // Geolocation
  document.getElementById('useLocationBtn')?.addEventListener('click', () => {
    if (!navigator.geolocation) {
      status!.textContent = 'Geolocation not supported.';
      return;
    }
    status!.textContent = 'Requesting location...';
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const { latitude: lat, longitude: lng, accuracy } = pos.coords;
      fromAddr.value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      
      try {
        const token = getCookie('csrftoken') || '';
        const r = await fetch('/taxi/set_location/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
          body: JSON.stringify({ lat, lng, accuracy, timestamp: pos.timestamp }),
        });
        
        if (r.ok) {
          status!.textContent = 'Location saved.';
          localStorage.setItem('user_location', JSON.stringify({lat, lng, accuracy}));
        } else {
          status!.textContent = 'Failed to sync backend location.';
        }
      } catch (err) {
        status!.textContent = 'Network error saving location.';
      }
    }, (err) => {
      status!.textContent = 'Error: ' + err.message;
    }, { enableHighAccuracy: true, timeout: 10000 });
  });

  // Submit handling
  form.addEventListener('submit', (e: Event) => {
    e.preventDefault();
    const from = fromAddr.value.trim();
    const to = toAddr.value.trim();
    
    if (!from || !to) return;
    
    const payload: TaxiRequest = { from, to, when: new Date().toISOString() };
    localStorage.setItem('last_taxi_request', JSON.stringify(payload, null, 2));
    
    status!.textContent = 'Redirecting to map...';
    window.location.href = '/taxi/map/';
  });
});