import http from 'k6/http';
import { check } from 'k6';

export let options = {
    scenarios: {
        high_load: {
            executor: 'constant-arrival-rate',
            rate: 150000, // 20,000 iterations per second
            timeUnit: '1s', // per second
            duration: '1m', // test duration
            preAllocatedVUs: 2000, // initial pool of virtual users
            maxVUs: 50000, // maximum virtual users
        },
    },
};

export default function () {
    let res = http.get('{{your-haproxy-url.com}}');
    check(res, {
        'status was 200': (r) => r.status === 200,
    });
}