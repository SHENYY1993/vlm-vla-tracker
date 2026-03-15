<template>
  <div class="app-container">
    <el-container>
      <!-- 头部 -->
      <el-header class="header">
        <div class="header-content">
          <h1>🤖 VLM/VLA Tracker</h1>
          <p class="subtitle">追踪最新视觉语言模型与视觉动作模型</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="refreshAll" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
            刷新全部
          </el-button>
        </div>
      </el-header>

      <el-main>
        <!-- 统计卡片 -->
        <el-row :gutter="20" class="stats-row">
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon">📄</div>
              <div class="stat-value">{{ stats.total_papers }}</div>
              <div class="stat-label">论文</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon">👁️</div>
              <div class="stat-value">{{ stats.vlm_papers }}</div>
              <div class="stat-label">VLM论文</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon">🤝</div>
              <div class="stat-value">{{ stats.vla_papers }}</div>
              <div class="stat-label">VLA论文</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card">
              <div class="stat-icon">📁</div>
              <div class="stat-value">{{ stats.total_projects }}</div>
              <div class="stat-label">开源项目</div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 标签页导航 -->
        <el-tabs v-model="activeTab" class="main-tabs">
          <!-- 论文Tab -->
          <el-tab-pane label="📄 论文" name="papers">
            <div class="tab-header">
              <el-button @click="refreshPapers" :loading="loadingPapers">
                <el-icon><Refresh /></el-icon> 刷新论文
              </el-button>
              <el-radio-group v-model="paperFilter" size="small">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="VLM">VLM</el-radio-button>
                <el-radio-button label="VLA">VLA</el-radio-button>
              </el-radio-group>
            </div>
            <div class="card-list">
              <el-card v-for="paper in filteredPapers" :key="paper._id" class="item-card">
                <template #header>
                  <div class="card-header">
                    <el-tag :type="paper.category === 'VLA' ? 'success' : 'primary'" size="small">
                      {{ paper.category }}
                    </el-tag>
                    <span class="paper-date">{{ paper.published_date }}</span>
                  </div>
                </template>
                <h3 class="item-title">
                  <a :href="paper.url" target="_blank">{{ paper.title }}</a>
                </h3>
                <p class="item-authors">{{ paper.authors }}</p>
                <p class="item-abstract">{{ paper.abstract }}</p>
                <p class="item-abstract" v-if="paper.chinese_translation">{{ paper.chinese_translation }}</p>
                <div class="card-footer">
                  <el-tag size="small" type="info">{{ paper.source }}</el-tag>
                </div>
              </el-card>
              <el-empty v-if="filteredPapers.length === 0" description="暂无论文数据"></el-empty>
            </div>
          </el-tab-pane>

          <!-- 项目Tab -->
          <el-tab-pane label="📁 项目" name="projects">
            <div class="tab-header">
              <el-button @click="refreshProjects" :loading="loadingProjects">
                <el-icon><Refresh /></el-icon> 刷新项目
              </el-button>
              <el-radio-group v-model="projectFilter" size="small">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="VLM">VLM</el-radio-button>
                <el-radio-button label="VLA">VLA</el-radio-button>
              </el-radio-group>
            </div>
            <div class="card-list">
              <el-card v-for="project in filteredProjects" :key="project._id" class="item-card">
                <template #header>
                  <div class="card-header">
                    <el-tag :type="project.category === 'VLA' ? 'success' : 'primary'" size="small">
                      {{ project.category }}
                    </el-tag>
                    <span v-if="project.stars" class="stars">
                      ⭐ {{ project.stars }}
                    </span>
                  </div>
                </template>
                <h3 class="item-title">
                  <a :href="project.url" target="_blank">{{ project.name }}</a>
                </h3>
                <p class="item-owner">by {{ project.owner }}</p>
                <p class="item-description">{{ project.description || '暂无简介' }}</p>
                <div class="card-footer">
                  <el-tag v-if="project.language" size="small" type="info">{{ project.language }}</el-tag>
                  <el-tag v-if="project.source" size="small">{{ project.source }}</el-tag>
                </div>
              </el-card>
              <el-empty v-if="filteredProjects.length === 0" description="暂无项目数据"></el-empty>
            </div>
          </el-tab-pane>

          <!-- 新闻Tab -->
          <el-tab-pane label="📰 新闻" name="news">
            <div class="tab-header">
              <el-button @click="refreshNews" :loading="loadingNews">
                <el-icon><Refresh /></el-icon> 刷新新闻
              </el-button>
              <el-radio-group v-model="newsFilter" size="small">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="VLM">VLM</el-radio-button>
                <el-radio-button label="VLA">VLA</el-radio-button>
              </el-radio-group>
            </div>
            <div class="card-list">
              <el-card v-for="news in filteredNews" :key="news._id" class="item-card">
                <template #header>
                  <div class="card-header">
                    <el-tag :type="news.category === 'VLA' ? 'success' : 'primary'" size="small">
                      {{ news.category }}
                    </el-tag>
                    <span v-if="news.published_date" class="news-date">
                      {{ news.published_date }}
                    </span>
                  </div>
                </template>
                <h3 class="item-title">
                  <a :href="news.url" target="_blank">{{ news.title }}</a>
                </h3>
                <p class="item-content">{{ news.content }}</p>
                <div class="card-footer">
                  <el-tag size="small" type="info">{{ news.source }}</el-tag>
                </div>
              </el-card>
              <el-empty v-if="filteredNews.length === 0" description="暂无新闻数据"></el-empty>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const API_BASE = '/api'

// 状态
const activeTab = ref('papers')
const papers = ref([])
const projects = ref([])
const news = ref([])
const stats = ref({ total_papers: 0, vlm_papers: 0, vla_papers: 0, total_projects: 0 })
const paperFilter = ref('all')
const projectFilter = ref('all')
const newsFilter = ref('all')
const refreshing = ref(false)
const loadingPapers = ref(false)
const loadingProjects = ref(false)
const loadingNews = ref(false)

// 过滤
const filteredPapers = computed(() => {
  if (paperFilter.value === 'all') return papers.value
  return papers.value.filter(p => p.category === paperFilter.value)
})

const filteredProjects = computed(() => {
  if (projectFilter.value === 'all') return projects.value
  return projects.value.filter(p => p.category === projectFilter.value)
})

const filteredNews = computed(() => {
  if (newsFilter.value === 'all') return news.value
  return news.value.filter(n => n.category === newsFilter.value)
})

// API调用
async function fetchAll() {
  try {
    const [allData, statsData] = await Promise.all([
      axios.get(`${API_BASE}/all`),
      axios.get(`${API_BASE}/stats`)
    ])
    papers.value = allData.data.papers || []
    projects.value = allData.data.projects || []
    news.value = allData.data.news || []
    stats.value = statsData.data
  } catch (e) {
    console.error('Fetch error:', e)
    ElMessage.error('获取数据失败，请确保后端服务已启动')
  }
}

async function refreshPapers() {
  loadingPapers.value = true
  try {
    const res = await axios.post(`${API_BASE}/papers/refresh`)
    ElMessage.success(res.data.message)
    await fetchAll()
  } catch (e) {
    ElMessage.error('刷新失败')
  } finally {
    loadingPapers.value = false
  }
}

async function refreshProjects() {
  loadingProjects.value = true
  try {
    const res = await axios.post(`${API_BASE}/projects/refresh`)
    ElMessage.success(res.data.message)
    await fetchAll()
  } catch (e) {
    ElMessage.error('刷新失败')
  } finally {
    loadingProjects.value = false
  }
}

async function refreshNews() {
  loadingNews.value = true
  try {
    const res = await axios.post(`${API_BASE}/news/refresh`)
    ElMessage.success(res.data.message)
    await fetchAll()
  } catch (e) {
    ElMessage.error('刷新失败')
  } finally {
    loadingNews.value = false
  }
}

async function refreshAll() {
  refreshing.value = true
  try {
    const res = await axios.post(`${API_BASE}/refresh-all`)
    ElMessage.success(`刷新完成：${res.data.papers_count} 篇论文，${res.data.projects_count} 个项目`)
    await fetchAll()
  } catch (e) {
    ElMessage.error('刷新失败，请确保后端服务已启动')
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  fetchAll()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
}

.header-content h1 {
  font-size: 28px;
  margin-bottom: 5px;
}

.subtitle {
  font-size: 14px;
  opacity: 0.9;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 10px;
}

.stat-card .el-card__body {
  padding: 20px;
}

.stat-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #667eea;
}

.stat-label {
  color: #666;
  margin-top: 5px;
}

.main-tabs {
  background: white;
  border-radius: 8px;
  padding: 20px;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.item-card {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.paper-date, .stars {
  color: #999;
  font-size: 14px;
}

.item-title {
  font-size: 16px;
  margin: 10px 0;
  line-height: 1.4;
}

.item-title a {
  color: #333;
  text-decoration: none;
}

.item-title a:hover {
  color: #667eea;
}

.item-authors, .item-owner {
  color: #666;
  font-size: 14px;
  margin-bottom: 10px;
}

.item-abstract, .item-description {
  color: #555;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 16;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 256px;
}

.card-footer {
  display: flex;
  gap: 10px;
}
</style>