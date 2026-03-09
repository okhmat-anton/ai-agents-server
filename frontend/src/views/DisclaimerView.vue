<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="10" md="8" lg="7">
        <v-card class="pa-6" elevation="8">
          <v-card-title class="text-center pb-4">
            <v-icon size="48" color="warning" class="mb-3">mdi-shield-alert</v-icon>
            <div class="text-h4 font-weight-bold">Legal Disclaimer</div>
            <div class="text-subtitle-1 text-grey mt-1">
              Please read and accept to continue
            </div>
          </v-card-title>

          <v-divider class="mb-4" />

          <v-card-text
            class="disclaimer-text overflow-y-auto pa-4"
            style="max-height: 55vh; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;"
          >
            <div class="text-h5 font-weight-bold mb-4 text-center">
              TERMS OF USE AND DISCLAIMER OF LIABILITY
            </div>

            <div class="text-body-2 text-grey mb-6 text-center">
              Last Updated: {{ currentDate }}
            </div>

            <p class="text-body-1 mb-4 font-weight-bold">
              IMPORTANT — PLEASE READ CAREFULLY BEFORE USING THIS PLATFORM. BY ACCESSING OR USING THE AI AGENTS SERVER PLATFORM ("PLATFORM"), YOU ACKNOWLEDGE THAT YOU HAVE READ, UNDERSTOOD, AND AGREE TO BE BOUND BY THE FOLLOWING TERMS AND CONDITIONS. IF YOU DO NOT AGREE TO THESE TERMS, YOU MUST NOT USE THE PLATFORM.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">1. DEFINITIONS</div>
            <p class="text-body-1 mb-3">
              1.1. <strong>"Platform"</strong> refers to the AI Agents Server software, including but not limited to all associated services, APIs, interfaces, agents, models, tools, integrations, outputs, and any content generated or processed through the system.
            </p>
            <p class="text-body-1 mb-3">
              1.2. <strong>"User"</strong> or <strong>"You"</strong> refers to any individual, entity, or organization that accesses, uses, operates, or otherwise interacts with the Platform.
            </p>
            <p class="text-body-1 mb-3">
              1.3. <strong>"Operator"</strong> refers to the person, entity, or organization that deploys, maintains, or administers this instance of the Platform.
            </p>
            <p class="text-body-1 mb-3">
              1.4. <strong>"AI Output"</strong> refers to any text, code, data, recommendations, actions, files, analysis, or other content generated, produced, modified, or processed by the artificial intelligence agents, language models, or automated systems operating within the Platform.
            </p>
            <p class="text-body-1 mb-3">
              1.5. <strong>"Third-Party Services"</strong> refers to any external services, APIs, language models, or integrations used by or connected to the Platform, including but not limited to Ollama, OpenAI, Anthropic, and any other AI model providers.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">2. NATURE OF THE PLATFORM</div>
            <p class="text-body-1 mb-3">
              2.1. The Platform is an experimental software tool designed for managing and interacting with artificial intelligence agents. The Platform utilizes large language models (LLMs) and other AI technologies to generate content, execute tasks, process data, and perform automated actions.
            </p>
            <p class="text-body-1 mb-3">
              2.2. AI technology is inherently probabilistic and may produce inaccurate, incomplete, biased, misleading, or entirely fabricated results. The Platform does not guarantee the accuracy, reliability, completeness, timeliness, or fitness for any particular purpose of any AI Output.
            </p>
            <p class="text-body-1 mb-3">
              2.3. The Platform is provided on an "AS IS" and "AS AVAILABLE" basis without any warranties of any kind, whether express, implied, statutory, or otherwise.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">3. COMPLETE DISCLAIMER OF WARRANTIES</div>
            <p class="text-body-1 mb-3">
              3.1. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE OPERATOR EXPRESSLY DISCLAIMS ALL WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR STATUTORY, INCLUDING BUT NOT LIMITED TO:
            </p>
            <ul class="text-body-1 mb-3 ml-6">
              <li class="mb-1">(a) IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT;</li>
              <li class="mb-1">(b) WARRANTIES ARISING OUT OF COURSE OF DEALING, USAGE, OR TRADE PRACTICE;</li>
              <li class="mb-1">(c) ANY WARRANTY THAT THE PLATFORM WILL BE UNINTERRUPTED, ERROR-FREE, SECURE, OR FREE OF VIRUSES OR OTHER HARMFUL COMPONENTS;</li>
              <li class="mb-1">(d) ANY WARRANTY REGARDING THE ACCURACY, RELIABILITY, COMPLETENESS, OR TIMELINESS OF ANY AI OUTPUT, DATA, OR INFORMATION PROVIDED THROUGH THE PLATFORM;</li>
              <li class="mb-1">(e) ANY WARRANTY THAT THE PLATFORM WILL MEET YOUR REQUIREMENTS OR EXPECTATIONS.</li>
            </ul>
            <p class="text-body-1 mb-3">
              3.2. No advice, information, or output obtained through the Platform shall create any warranty not expressly stated in these Terms.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">4. LIMITATION OF LIABILITY</div>
            <p class="text-body-1 mb-3">
              4.1. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL THE OPERATOR, ITS AFFILIATES, DIRECTORS, OFFICERS, EMPLOYEES, AGENTS, SUPPLIERS, OR LICENSORS BE LIABLE FOR ANY OF THE FOLLOWING, WHETHER BASED ON WARRANTY, CONTRACT, TORT (INCLUDING NEGLIGENCE), STRICT LIABILITY, OR ANY OTHER LEGAL THEORY:
            </p>
            <ul class="text-body-1 mb-3 ml-6">
              <li class="mb-1">(a) ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES;</li>
              <li class="mb-1">(b) ANY LOSS OF PROFITS, REVENUE, BUSINESS, SAVINGS, GOODWILL, OR DATA;</li>
              <li class="mb-1">(c) ANY LOSS OR DAMAGE ARISING FROM RELIANCE ON AI OUTPUT;</li>
              <li class="mb-1">(d) ANY LOSS OR DAMAGE CAUSED BY THE EXECUTION OF CODE, COMMANDS, OR SCRIPTS GENERATED OR RECOMMENDED BY THE PLATFORM;</li>
              <li class="mb-1">(e) ANY LOSS OR DAMAGE RESULTING FROM UNAUTHORIZED ACCESS TO OR ALTERATION OF YOUR DATA;</li>
              <li class="mb-1">(f) ANY LOSS OR DAMAGE CAUSED BY SYSTEM FAILURES, DATA CORRUPTION, OR SECURITY BREACHES;</li>
              <li class="mb-1">(g) ANY DAMAGES ARISING FROM THE USE OF THIRD-PARTY SERVICES OR INTEGRATIONS;</li>
              <li class="mb-1">(h) ANY OTHER LOSS OR DAMAGE OF ANY KIND, EVEN IF THE OPERATOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.</li>
            </ul>
            <p class="text-body-1 mb-3">
              4.2. IN ANY EVENT, THE TOTAL AGGREGATE LIABILITY OF THE OPERATOR FOR ALL CLAIMS ARISING OUT OF OR RELATED TO THE USE OF THE PLATFORM SHALL NOT EXCEED THE AMOUNT, IF ANY, PAID BY YOU TO THE OPERATOR FOR ACCESS TO THE PLATFORM DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM, OR ONE HUNDRED US DOLLARS ($100.00), WHICHEVER IS LESS.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">5. ASSUMPTION OF RISK</div>
            <p class="text-body-1 mb-3">
              5.1. You expressly acknowledge and agree that your use of the Platform is entirely at your own risk. You assume full responsibility for all consequences arising from your use of the Platform, including but not limited to:
            </p>
            <ul class="text-body-1 mb-3 ml-6">
              <li class="mb-1">(a) Any decisions made or actions taken based on AI Output;</li>
              <li class="mb-1">(b) Any code, scripts, or commands executed on your systems as a result of AI recommendations;</li>
              <li class="mb-1">(c) Any data loss, system damage, or security incidents;</li>
              <li class="mb-1">(d) Any financial, legal, reputational, or personal harm resulting from the use of AI Output;</li>
              <li class="mb-1">(e) Any consequences of granting the Platform access to your files, systems, terminals, or networks;</li>
              <li class="mb-1">(f) Any consequences arising from autonomous agent actions, including unintended or erroneous operations.</li>
            </ul>
            <p class="text-body-1 mb-3">
              5.2. You acknowledge that AI agents operating within the Platform may perform autonomous actions, including but not limited to creating files, modifying data, executing code, accessing external services, and making network requests. You accept full responsibility for enabling, configuring, and overseeing such actions.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">6. AI OUTPUT DISCLAIMER</div>
            <p class="text-body-1 mb-3">
              6.1. AI Output may contain errors, inaccuracies, omissions, biases, hallucinations, or fabricated information. You must independently verify all AI Output before relying on it for any purpose.
            </p>
            <p class="text-body-1 mb-3">
              6.2. AI Output does not constitute professional advice of any kind, including but not limited to legal, medical, financial, accounting, engineering, or security advice. You should consult qualified professionals before making any decisions based on AI Output.
            </p>
            <p class="text-body-1 mb-3">
              6.3. The Operator makes no representations or warranties regarding the intellectual property status of any AI Output. You are solely responsible for ensuring that your use of AI Output does not infringe upon the intellectual property rights of any third party.
            </p>
            <p class="text-body-1 mb-3">
              6.4. AI models used by the Platform may produce different results at different times for the same input. Past performance or accuracy of AI Output is not indicative of future results.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">7. SECURITY AND DATA RISKS</div>
            <p class="text-body-1 mb-3">
              7.1. The Platform may process, store, and transmit data including but not limited to user input, chat histories, files, and system information. The Operator does not guarantee the confidentiality, integrity, or availability of any data processed by the Platform.
            </p>
            <p class="text-body-1 mb-3">
              7.2. You acknowledge that data submitted to AI models may be processed by Third-Party Services, and you accept any associated privacy and security risks.
            </p>
            <p class="text-body-1 mb-3">
              7.3. You are solely responsible for maintaining adequate backups of any data that may be accessed, processed, or modified by the Platform or its AI agents.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">8. INDEMNIFICATION</div>
            <p class="text-body-1 mb-3">
              8.1. You agree to indemnify, defend, and hold harmless the Operator, its affiliates, directors, officers, employees, agents, suppliers, and licensors from and against any and all claims, demands, actions, liabilities, damages, losses, costs, and expenses (including reasonable attorneys' fees) arising out of or related to:
            </p>
            <ul class="text-body-1 mb-3 ml-6">
              <li class="mb-1">(a) Your use of or access to the Platform;</li>
              <li class="mb-1">(b) Your reliance on any AI Output;</li>
              <li class="mb-1">(c) Your violation of these Terms;</li>
              <li class="mb-1">(d) Your violation of any applicable law, regulation, or third-party right;</li>
              <li class="mb-1">(e) Any claim by a third party arising from your use of AI Output or the Platform.</li>
            </ul>

            <div class="text-h6 font-weight-bold mt-6 mb-2">9. THIRD-PARTY SERVICES</div>
            <p class="text-body-1 mb-3">
              9.1. The Platform integrates with or relies upon Third-Party Services over which the Operator has no control. The Operator makes no representations or warranties regarding the availability, accuracy, security, or performance of any Third-Party Services.
            </p>
            <p class="text-body-1 mb-3">
              9.2. Your use of Third-Party Services through the Platform is subject to the respective terms of service and privacy policies of those third parties.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">10. MODIFICATIONS TO TERMS</div>
            <p class="text-body-1 mb-3">
              10.1. The Operator reserves the right to modify these Terms at any time. Material changes will require renewed acceptance. Continued use of the Platform after modification constitutes acceptance of the updated Terms.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">11. SEVERABILITY</div>
            <p class="text-body-1 mb-3">
              11.1. If any provision of these Terms is held to be invalid, illegal, or unenforceable by a court of competent jurisdiction, such provision shall be modified to the minimum extent necessary to make it valid and enforceable, or if modification is not possible, shall be severed, and the remaining provisions shall continue in full force and effect.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">12. GOVERNING LAW</div>
            <p class="text-body-1 mb-3">
              12.1. These Terms shall be governed by and construed in accordance with the laws of the jurisdiction in which the Operator is established, without regard to its conflict of law provisions. Any disputes arising out of or relating to these Terms shall be subject to the exclusive jurisdiction of the courts of that jurisdiction.
            </p>

            <div class="text-h6 font-weight-bold mt-6 mb-2">13. ENTIRE AGREEMENT</div>
            <p class="text-body-1 mb-3">
              13.1. These Terms constitute the entire agreement between You and the Operator regarding the use of the Platform and supersede all prior or contemporaneous understandings, agreements, or communications, whether written or oral, regarding such subject matter.
            </p>

            <v-divider class="my-4" />

            <p class="text-body-1 font-weight-bold text-center">
              BY CLICKING "I ACCEPT" BELOW, YOU ACKNOWLEDGE THAT YOU HAVE READ, UNDERSTOOD, AND AGREE TO BE BOUND BY ALL OF THE TERMS AND CONDITIONS SET FORTH IN THIS DISCLAIMER. YOU FURTHER ACKNOWLEDGE THAT THIS DISCLAIMER CONSTITUTES A BINDING LEGAL AGREEMENT BETWEEN YOU AND THE OPERATOR.
            </p>
          </v-card-text>

          <v-divider class="mt-4 mb-4" />

          <v-card-actions class="justify-center pb-2">
            <v-btn
              variant="outlined"
              color="grey"
              size="large"
              class="mr-4"
              @click="handleDecline"
            >
              <v-icon start>mdi-close</v-icon>
              Decline
            </v-btn>
            <v-btn
              color="success"
              size="large"
              variant="elevated"
              :loading="loading"
              @click="handleAccept"
            >
              <v-icon start>mdi-check-circle</v-icon>
              I Accept
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)

const currentDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
})

const handleAccept = async () => {
  loading.value = true
  try {
    await api.post('/auth/disclaimer/accept')
    await auth.fetchUser()
    router.push('/')
  } catch (e) {
    console.error('Failed to accept disclaimer:', e)
  } finally {
    loading.value = false
  }
}

const handleDecline = () => {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.disclaimer-text {
  line-height: 1.7;
}
</style>
