/*
 * Copyright (c) 2026.
 */

interface LatestSample<sample_type_t> {
  command bool available();
  command error_t get(sample_type_t* sample);
}
