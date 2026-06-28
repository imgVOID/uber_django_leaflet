import { LocationData, NominatimResult, TaxiRequestPayload } from './types/taxi';

const API = {
    async search(query: string): Promise<NominatimResult[]> {
        const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5`);
        return res.ok ? res.json() : [];
    },
    async reverse(lat: number, lon: number): Promise<string> {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`);
        const data = await res.json();
        return data.display_name || `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
    },
    async startRide(payload: TaxiRequestPayload): Promise<{ ride_id: number } | null> {
        const token = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)?.value;
        const res = await fetch('//start/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token || '' },
            body: JSON.stringify(payload),
        });
        return res.ok ? res.json() : null;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('taxiForm') as HTMLFormElement;
    const fromInput = document.getElementById('from_addr') as HTMLInputElement;
    const toInput = document.getElementById('to_addr') as HTMLInputElement;
    const status = document.getElementById('status')!;

    const setAddress = (input: HTMLInputElement, name: string, lat: number, lon: number) => {
        input.value = name;
        input.dataset.lat = lat.toString();
        input.dataset.lng = lon.toString();
    };

    const verifyAddress = async (input: HTMLInputElement, containerId: string) => {
        const container = document.getElementById(containerId)!;
        const results = await API.search(input.value);
        container.innerHTML = '';
        container.classList.remove('d-none');
        
        results.forEach(item => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'list-group-item list-group-item-action';
            btn.textContent = item.display_name;
            btn.onclick = () => {
                setAddress(input, item.display_name, parseFloat(item.lat), parseFloat(item.lon));
                container.classList.add('d-none');
            };
            container.appendChild(btn);
        });
    };

    document.getElementById('checkFromBtn')?.addEventListener('click', () => verifyAddress(fromInput, 'fromResults'));
    document.getElementById('checkToBtn')?.addEventListener('click', () => verifyAddress(toInput, 'toResults'));

    document.getElementById('useLocationBtn')?.addEventListener('click', () => {
        status.textContent = 'GPS...';
        navigator.geolocation.getCurrentPosition(async (pos) => {
            const { latitude, longitude } = pos.coords;
            const address = await API.reverse(latitude, longitude);
            setAddress(fromInput, address, latitude, longitude);
            status.textContent = 'Location set.';
        });
    });

    form.onsubmit = async (e) => {
        e.preventDefault();
        status.textContent = 'Creating ride...';

        const payload: TaxiRequestPayload = {
            pickup_address: fromInput.value,
            dropoff_address: toInput.value || "",
            pickup_lat: parseFloat(fromInput.dataset.lat || '0'),
            pickup_lng: parseFloat(fromInput.dataset.lng || '0'),
            dropoff_lat: toInput.dataset.lat ? parseFloat(toInput.dataset.lat) : null,
            dropoff_lng: toInput.dataset.lng ? parseFloat(toInput.dataset.lng) : null
        };

        const result = await API.startRide(payload);
        if (result?.ride_id) {
            window.location.href = '/map/';
        } else {
            status.textContent = 'Error: Could not create ride.';
        }
    };
});