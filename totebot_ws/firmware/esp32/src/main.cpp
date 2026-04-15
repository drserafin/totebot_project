#include <Arduino.h>
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/int32_multi_array.h>
#include <rmw_microros/rmw_microros.h>
#include <ESP32Encoder.h>

/*
=============================================================================
🤖 TOTEBOT ESP32 SENSOR NODE (ENCODERS)
=============================================================================
This program reads three encoders using the ESP32's hardware PCNT unit. 
It packages these three counts into a single std_msgs/Int32MultiArray 
and publishes them to the Raspberry Pi at 20Hz. 
=============================================================================
*/

// --- Encoder Setup ---
ESP32Encoder left_encoder;
ESP32Encoder right_encoder;
ESP32Encoder lifter_encoder;

// Define your GPIO pins here
const int LEFT_ENC_A = 34; 
const int LEFT_ENC_B = 35;
const int RIGHT_ENC_A = 32; 
const int RIGHT_ENC_B = 33;
const int LIFTER_ENC_A = 25; 
const int LIFTER_ENC_B = 26;

rcl_publisher_t publisher;
std_msgs__msg__Int32MultiArray msg;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
rcl_timer_t timer;
rclc_executor_t executor;

enum states {
  WAITING_AGENT,
  AGENT_AVAILABLE,
  AGENT_CONNECTED,
  AGENT_DISCONNECTED
} state;

#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){return false;}}

void timer_callback(rcl_timer_t * timer, int64_t last_call_time) {
  if (timer != NULL) {
    // Index into the array with [0], [1], [2] — not the pointer itself
    msg.data.data[0] = (int32_t)left_encoder.getCount();
    msg.data.data[1] = (int32_t)right_encoder.getCount();
    msg.data.data[2] = (int32_t)lifter_encoder.getCount();
    
    // Publish it to the Raspberry Pi
    (void) rcl_publish(&publisher, &msg, NULL);
  }
}

// --- Build the Node ---
bool create_entities() {
  allocator = rcl_get_default_allocator();
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));
  RCCHECK(rclc_node_init_default(&node, "esp32_encoder_node", "", &support));

  // --- Dynamic Memory Allocation ---
  msg.data.capacity = 3;
  msg.data.size = 3;
  msg.data.data = (int32_t*) malloc(msg.data.capacity * sizeof(int32_t));

  RCCHECK(rclc_publisher_init_default(
    &publisher, &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32MultiArray),
    "encoder_array"));

  RCCHECK(rclc_timer_init_default(&timer, &support, RCL_MS_TO_NS(50), timer_callback));
  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_timer(&executor, &timer));
  return true;
}

void destroy_entities() {
  rmw_context_t * rmw_context = rcl_context_get_rmw_context(&support.context);
  (void) rmw_uros_set_context_entity_destroy_session_timeout(rmw_context, 0);

  (void) rcl_publisher_fini(&publisher, &node);
  (void) rcl_timer_fini(&timer);
  (void) rclc_executor_fini(&executor);
  (void) rcl_node_fini(&node);
  (void) rclc_support_fini(&support);
  
  if (msg.data.data != NULL) {
    free(msg.data.data);
    msg.data.data = NULL; // Null after free to avoid dangling pointer
  }
}

void setup() {
  Serial.begin(115200);
  set_microros_serial_transports(Serial);
  
  left_encoder.attachFullQuad(LEFT_ENC_A, LEFT_ENC_B);
  right_encoder.attachFullQuad(RIGHT_ENC_A, RIGHT_ENC_B);
  lifter_encoder.attachFullQuad(LIFTER_ENC_A, LIFTER_ENC_B);
  
  left_encoder.clearCount(); 
  right_encoder.clearCount();
  lifter_encoder.clearCount();

  state = WAITING_AGENT; 
}

void loop() {
  switch (state) {
    case WAITING_AGENT:
      if (rmw_uros_ping_agent(100, 1) == RMW_RET_OK) {
        state = AGENT_AVAILABLE;
      }
      break;
    case AGENT_AVAILABLE:
      if (create_entities()) {
        state = AGENT_CONNECTED;
      } else {
        state = WAITING_AGENT;
        destroy_entities();
      }
      break;
    case AGENT_CONNECTED:
      if (rmw_uros_ping_agent(100, 1) == RMW_RET_OK) {
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10)); 
      } else {
        state = AGENT_DISCONNECTED;
      }
      break;
    case AGENT_DISCONNECTED:
      destroy_entities();
      state = WAITING_AGENT;
      break;
  }
  delay(10);
}