<template>
  <v-app>
    <router-view />
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top right">
      {{ snackbar.text }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { reactive, provide } from 'vue'

const snackbar = reactive({ show: false, text: '', color: 'success' })
const showSnackbar = (text, color = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}
provide('showSnackbar', showSnackbar)
</script>
