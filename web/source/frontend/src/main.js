import { mount } from 'svelte';
import App from './App.svelte';
import './style.css';

window.__observatory = { streams: {}, status: null, errors: [] };
mount(App, { target: document.getElementById('app') });
